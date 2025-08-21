"""Pipeline stage for enriching workflows with marketplace metadata."""
from abc import abstractmethod
from typing import Any, Dict, List, Optional, Tuple

import yaml

from validate_actions.domain_model import ast
from validate_actions.domain_model.ast import ActionMetadata, ExecAction, Workflow
from validate_actions.domain_model.primitives import String
from validate_actions.globals.problems import Problem, ProblemLevel, Problems
from validate_actions.globals.process_stage import ProcessStage
from validate_actions.globals.web_fetcher import WebFetcher


class MarketPlaceEnricher(ProcessStage[ast.Workflow, ast.Workflow]):
    """Interface for enriching workflows with marketplace metadata.

    Fetches action metadata from GitHub marketplace/repositories to enrich
    workflow AST with action input/output information and version data.
    """

    def __init__(self, web_fetcher: WebFetcher, problems: Problems) -> None:
        """Initialize the marketplace enricher.

        Args:
            web_fetcher: Web fetcher for making HTTP requests
            problems: Collection to append validation problems to
        """
        self._web_fetcher = web_fetcher
        self._problems = problems

    @abstractmethod
    def process(self, workflow: ast.Workflow) -> ast.Workflow:
        """Enrich workflow with marketplace metadata.

        Args:
            workflow: The workflow to enrich with marketplace data

        Returns:
            ast.Workflow: The enriched workflow with metadata attached to actions
        """
        pass


class DefaultMarketPlaceEnricher(MarketPlaceEnricher):
    """Enriches workflows with marketplace metadata for GitHub Actions.

    Fetches action metadata from GitHub repositories to provide input validation
    and version information for workflow actions. This is a defensive security
    tool component that validates action usage against their actual definitions.
    """

    def __init__(self, web_fetcher: WebFetcher, problems: Problems) -> None:
        """Initialize the marketplace enricher.

        Args:
            web_fetcher: Web fetcher for making HTTP requests
            problems: Collection to append validation problems to
        """
        super().__init__(web_fetcher, problems)
        self._RULE_NAME = "marketplace"

    def process(self, workflow: Workflow) -> Workflow:
        """Enrich workflow with marketplace metadata.

        Iterates through all job steps that use external actions and fetches
        their metadata from GitHub repositories. Attaches ActionMetadata to
        each ExecAction containing input requirements and available versions.

        Args:
            workflow: The workflow to enrich

        Returns:
            Workflow: The same workflow object with metadata attached to actions
        """
        for job in workflow.jobs_:
            for step in workflow.jobs_[job].steps_:
                if isinstance(step.exec, ExecAction):
                    required_inputs, possible_inputs = self._get_action_inputs(step.exec)
                    version_tags = self._get_action_tags(step.exec)
                    outputs = self._get_action_outputs(step.exec)
                    step.exec.metadata = ActionMetadata(
                        required_inputs=required_inputs,
                        possible_inputs=possible_inputs,
                        version_tags=version_tags,
                        outputs=outputs,
                    )
        return workflow

    def _get_action_inputs(self, action: ExecAction) -> Tuple[List[str], List[str]]:
        """Get required and optional inputs for a GitHub Action.

        Fetches the action.yml/action.yaml file from the action's repository
        and parses the input definitions to determine which inputs are required
        (no default value and marked as required) vs optional.

        Args:
            action: The ExecAction to get inputs for

        Returns:
            Tuple containing (required_inputs, optional_inputs) as lists of strings.
            Returns ([], []) if metadata cannot be fetched.
        """
        action_metadata = self._parse_action_yml(action)

        if action_metadata is None:
            self._problems.append(
                Problem(
                    action.pos,
                    ProblemLevel.WAR,
                    f"Couldn't fetch metadata for {action.uses_.string}. "
                    "Continuing validation without input validation.",
                    self._RULE_NAME,
                )
            )
            return [], []

        inputs = action_metadata.get("inputs", {})
        possible_inputs = list(inputs.keys())
        required_inputs = [
            key
            for key, value in inputs.items()
            if (value.get("required") is True and value.get("default") is None)
        ]
        return required_inputs, possible_inputs

    def _get_action_outputs(self, action: ExecAction) -> Dict[str, str]:
        """Get outputs for a GitHub Action.

        Fetches the action.yml/action.yaml file from the action's repository
        and parses the outputs definitions.

        Args:
            action: The ExecAction to get outputs for

        Returns:
            Dictionary mapping output names to their descriptions.
            Returns {} if metadata cannot be fetched.
        """
        action_metadata = self._parse_action_yml(action)

        if action_metadata is None:
            return {}

        outputs = action_metadata.get("outputs", {})
        return {key: value.get("description", "") for key, value in outputs.items()}

    def _parse_action_yml(self, action: ExecAction) -> Optional[Dict[str, Any]]:
        """Parse action.yml metadata from GitHub repository.

        Constructs URLs for action.yml/action.yaml files and attempts to fetch
        and parse them. Handles various action reference formats including
        versioned references and nested directory actions.

        Args:
            action: The ExecAction to fetch metadata for

        Returns:
            Parsed action metadata dictionary, or None if not found/parseable
        """
        if isinstance(action.uses_, String):
            slug = action.uses_.string
        elif isinstance(action.uses_, str):
            slug = action.uses_
        else:
            return None

        action_name, sep, tag = slug.partition("@")
        tags = [tag] if sep else ["main", "master"]

        directories = slug.split("/")
        for i, directory in enumerate(directories):
            dir_action, _, _ = directory.partition("@")
            directories[i] = dir_action

        github_base_url = "https://raw.githubusercontent.com/"
        for current_tag in tags:
            if len(directories) < 3:
                url_no_ext = f"{github_base_url}{action_name}/{current_tag}/action"
            else:
                url_no_ext = f"{github_base_url}{directories[0]}/{directories[1]}/{current_tag}"
                for directory in directories[2:]:
                    url_no_ext += f"/{directory}"
                url_no_ext += "/action"

            for ext in [".yml", ".yaml"]:
                response = self._web_fetcher.fetch(f"{url_no_ext}{ext}")
                if response is not None and response.status_code == 200:
                    try:
                        action_metadata = yaml.safe_load(response.text)
                        return action_metadata
                    except yaml.YAMLError:
                        continue
        return None

    def _get_action_tags(self, action: ExecAction) -> List[Dict[str, Any]]:
        """Get available version tags for a GitHub Action.

        Fetches tag information from the GitHub API to provide version
        validation capabilities. This helps detect usage of non-existent
        or deprecated versions.

        Args:
            action: The ExecAction to get tags for

        Returns:
            List of tag objects with 'name' and 'commit' fields.
            Returns empty list if unable to fetch or action doesn't exist.
        """
        if not isinstance(action.uses_, String):
            return []

        slug = action.uses_.string
        action_name, _, _ = slug.partition("@")

        parts = action_name.split("/")
        if len(parts) < 2:
            return []

        repo_slug = f"{parts[0]}/{parts[1]}"
        url = f"https://api.github.com/repos/{repo_slug}/tags"

        response = self._web_fetcher.fetch(url)
        if response is not None and response.status_code == 200:
            try:
                tags = response.json()
                return tags if isinstance(tags, list) else []
            except (ValueError, KeyError, TypeError):
                pass

        self._problems.append(
            Problem(
                action.pos,
                ProblemLevel.WAR,
                f"Couldn't fetch version tags for {repo_slug}. "
                "Continuing without version validation.",
                self._RULE_NAME,
            )
        )
        return []
