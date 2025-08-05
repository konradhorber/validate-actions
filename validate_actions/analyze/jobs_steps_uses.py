import logging
from typing import Generator, List, Tuple, Union

import requests

from validate_actions.analyze.rule import Rule
from validate_actions.analyze.support_functions import (
    compare_semantic_versions,
    get_action_tags,
    get_current_action_version,
    is_commit_sha,
    parse_action,
    parse_semantic_version,
    resolve_version_to_latest,
)
from validate_actions.core.problems import Problem, ProblemLevel
from validate_actions.domain_model.ast import ExecAction

logger = logging.getLogger(__name__)


class JobsStepsUses(Rule):
    """
    Validates the `uses:` field in workflow steps.
    """

    NAME = "jobs-steps-uses"

    def check(
        self,
    ) -> Generator[Problem, None, None]:
        """
        Validates all actions in the workflow.

        Args:
            workflow (Workflow): The workflow to validate.
            schema (dict, optional): The schema to validate against. Defaults
                to None.

        Yields:
            Problem: Problems found during validation.
        """
        return self.check_single_action()

    def check_single_action(
        self,
    ) -> Generator[Problem, None, None]:
        """
        Validates actions individually without context declared by `uses:` in
        the workflow steps.

        Args:
            workflow (Workflow): The workflow to validate.

        Yields:
            Problem: Problems found during validation.
        """
        actions = []
        for job in self.workflow.jobs_.values():
            steps = job.steps_
            for step in steps:
                if isinstance(step.exec, ExecAction):
                    actions.append(step.exec)

        for action in actions:
            yield from self.not_using_version_spec(action)
            yield from self.is_outdated_version(action)

            input_result = self.get_inputs(action)
            if isinstance(input_result, Problem):
                yield input_result
                return
            else:
                required_inputs, possible_inputs = input_result

            if len(action.with_) == 0:
                if len(required_inputs) == 0:
                    continue
                else:
                    yield from self.misses_required_input(action, required_inputs)
            else:
                yield from self.check_required_inputs(action, required_inputs)
                yield from self.uses_non_defined_input(action, possible_inputs)

    def not_using_version_spec(self, action: ExecAction) -> Generator[Problem, None, None]:
        """
        Checks if an action specifies a version using `@version`. If not, a
        warning is generated.

        Args:
            action (ExecAction): The action to validate.

        Yields:
            Problem: Warning if version is not specified.
        """
        slug = action.uses_.string
        if "@" not in slug:
            # Get latest version for suggestion
            latest_version = get_current_action_version(slug)
            version_suggestion = f"@{latest_version}" if latest_version else "@version"

            problem = Problem(
                action.pos,
                ProblemLevel.WAR,
                f"Using specific version of {slug} is recommended. "
                f"Consider using {slug}{version_suggestion}",
                self.NAME,
            )
            if self.fix:
                version = get_current_action_version(slug)
                if version:
                    new_slug = f"{slug}@{version}"
                    problem = self.fixer.edit_yaml_at_position(
                        action.uses_.pos.idx,
                        slug,
                        new_slug,
                        problem,
                        f"Fixed '{slug}' to include version to '{new_slug}'",
                    )
                    action.uses_.string = f"{slug}@{version}"
            yield problem

    def is_outdated_version(self, action: ExecAction) -> Generator[Problem, None, None]:
        """
        Checks if an action is using an outdated version and generates warnings.

        Handles full versions (v4.2.1), partial versions (v4), and commit SHAs.
        Uses GitHub Actions semantics where 'v4' resolves to latest 'v4.x.x'.

        Args:
            action (ExecAction): The action to validate.

        Yields:
            Problem: Warning if version is outdated, with auto-fix support.
        """
        slug = action.uses_.string

        # Skip actions without version specs - handled by not_using_version_spec
        if "@" not in slug:
            return

        # Extract slug and version
        action_slug, version_spec = slug.rsplit("@", 1)

        # Skip empty version specs
        if not version_spec:
            return

        try:
            # Get the current latest version for this action
            current_latest = get_current_action_version(action_slug)
            if not current_latest:
                # Can't check if we can't fetch action metadata (e.g., private repo)
                return

            # Parse the current latest version
            current_parsed = parse_semantic_version(current_latest)
            if not current_parsed or None in current_parsed:
                # Current version is not a valid semantic version
                return

            # Type narrowing: we've validated all components are not None
            # Cast is safe because we checked None not in current_parsed above
            current_tuple: Tuple[int, int, int] = (
                current_parsed[0],
                current_parsed[1] or 0,  # This won't happen due to validation above
                current_parsed[2] or 0,  # This won't happen due to validation above
            )

            # Handle different version spec types
            if is_commit_sha(version_spec):
                # Handle commit SHA by finding its corresponding version
                yield from self._handle_commit_sha_version(
                    action, action_slug, version_spec, current_latest, current_tuple
                )
            else:
                # Handle semantic version (partial or full)
                yield from self._handle_semantic_version(
                    action, action_slug, version_spec, current_latest, current_tuple
                )

        except (requests.RequestException, ValueError, TypeError, IndexError) as e:
            # Graceful handling of expected errors during version checking
            # Network issues, parsing errors, or malformed version data
            logger.debug(f"Version check failed for {action_slug}: {e}")
            return

    def _handle_commit_sha_version(
        self,
        action: ExecAction,
        action_slug: str,
        commit_sha: str,
        current_latest: str,
        current_tuple: Tuple[int, int, int],
    ) -> Generator[Problem, None, None]:
        """Handle version checking for commit SHA specifications."""
        # Get all tags to find which version this commit corresponds to
        tags = get_action_tags(action_slug)
        if not tags:
            return

        # Find the tag that matches this commit SHA
        commit_version = None
        # Ensure minimum meaningful SHA length for matching
        if len(commit_sha) < 7:
            return

        for tag in tags:
            tag_commit = tag.get("commit", {}).get("sha", "")
            # Only match if the tag's commit starts with our SHA (prefix match)
            # Require at least 7 characters for confident matching
            if tag_commit and tag_commit.startswith(commit_sha):
                commit_version = tag.get("name")
                break

        if not commit_version:
            # Unknown commit, generate warning with generic message
            problem = Problem(
                action.pos,
                ProblemLevel.WAR,
                f"Action {action_slug} uses commit SHA which may be outdated. "
                f"Current latest version is {current_latest}. Consider using versioned tags.",
                self.NAME,
            )
            if self.fix:
                problem = self.fixer.edit_yaml_at_position(
                    action.uses_.pos.idx + len(action_slug) + 1,  # +1 for '@'
                    commit_sha,
                    current_latest,
                    problem,
                    f"Updated commit SHA to latest version {current_latest}",
                )
                action.uses_.string = f"{action_slug}@{current_latest}"
            yield problem
            return

        # Parse the commit's corresponding version
        commit_parsed = parse_semantic_version(commit_version)
        if not commit_parsed or None in commit_parsed:
            return

        # Type narrowing: we've validated all components are not None
        commit_tuple: Tuple[int, int, int] = (
            commit_parsed[0],
            commit_parsed[1] or 0,  # This won't happen due to validation above
            commit_parsed[2] or 0,  # This won't happen due to validation above
        )

        # Compare versions
        outdated_level = compare_semantic_versions(current_tuple, commit_tuple)
        if outdated_level:
            problem = Problem(
                action.pos,
                ProblemLevel.WAR,
                f"Action {action_slug} uses commit SHA "
                f"(corresponds to {commit_version}) which is {outdated_level} "
                f"version outdated. Current latest is {current_latest}.",
                self.NAME,
            )
            if self.fix:
                problem = self.fixer.edit_yaml_at_position(
                    action.uses_.pos.idx + len(action_slug) + 1,  # +1 for '@'
                    commit_sha,
                    current_latest,
                    problem,
                    f"Updated outdated commit SHA to latest version {current_latest}",
                )
                action.uses_.string = f"{action_slug}@{current_latest}"
            yield problem

    def _handle_semantic_version(
        self,
        action: ExecAction,
        action_slug: str,
        version_spec: str,
        current_latest: str,
        current_tuple: Tuple[int, int, int],
    ) -> Generator[Problem, None, None]:
        """Handle version checking for semantic version specifications."""
        # Parse the used version spec
        used_parsed = parse_semantic_version(version_spec)
        if not used_parsed:
            # Invalid version format, skip
            return

        # Check if this is a partial version that needs resolution
        if None in used_parsed:
            # Resolve partial version (e.g., v4 -> v4.2.2)
            resolved_version = resolve_version_to_latest(action_slug, version_spec)
            if not resolved_version:
                # Version spec cannot be resolved - this is a problem!
                # E.g., actions/cache@v2 when only v3+ exists
                problem = Problem(
                    action.pos,
                    ProblemLevel.WAR,
                    f"Action {action_slug} uses outdated {version_spec} which "
                    f"cannot be resolved to any available version. "
                    f"Current latest is {current_latest}.",
                    self.NAME,
                )
                if self.fix:
                    problem = self.fixer.edit_yaml_at_position(
                        action.uses_.pos.idx + len(action_slug) + 1,  # +1 for '@'
                        version_spec,
                        current_latest,
                        problem,
                        f"Fixed unresolvable version {version_spec} to latest {current_latest}",
                    )
                    action.uses_.string = f"{action_slug}@{current_latest}"
                yield problem
                return

            # Parse the resolved version
            resolved_parsed = parse_semantic_version(resolved_version)
            if not resolved_parsed or None in resolved_parsed:
                return

            # Type narrowing: we've validated all components are not None
            resolved_tuple: Tuple[int, int, int] = (
                resolved_parsed[0],
                resolved_parsed[1] or 0,  # This won't happen due to validation above
                resolved_parsed[2] or 0,  # This won't happen due to validation above
            )

            # For partial versions, compare the resolved version
            outdated_level = compare_semantic_versions(current_tuple, resolved_tuple)
            if outdated_level:
                problem = Problem(
                    action.pos,
                    ProblemLevel.WAR,
                    f"Action {action_slug} uses {version_spec} "
                    f"(resolves to {resolved_version}) which is {outdated_level} "
                    f"version outdated. Current latest is {current_latest}.",
                    self.NAME,
                )
                if self.fix:
                    problem = self.fixer.edit_yaml_at_position(
                        action.uses_.pos.idx + len(action_slug) + 1,  # +1 for '@'
                        version_spec,
                        current_latest,
                        problem,
                        f"Fixed outdated version {version_spec} to latest {current_latest}",
                    )
                    action.uses_.string = f"{action_slug}@{current_latest}"
                yield problem
        else:
            # Full version specification - validate it's complete
            if None in used_parsed:
                # This shouldn't happen for full versions, but safety check
                return

            # Type narrowing: we've validated all components are not None
            full_tuple: Tuple[int, int, int] = (
                used_parsed[0],
                used_parsed[1] or 0,  # This won't happen due to validation above
                used_parsed[2] or 0,  # This won't happen due to validation above
            )

            # Compare versions
            outdated_level = compare_semantic_versions(current_tuple, full_tuple)
            if outdated_level:
                problem = Problem(
                    action.pos,
                    ProblemLevel.WAR,
                    f"Action {action_slug} uses {version_spec} which is "
                    f"{outdated_level} version outdated. Current latest is {current_latest}.",
                    self.NAME,
                )
                if self.fix:
                    problem = self.fixer.edit_yaml_at_position(
                        action.uses_.pos.idx + len(action_slug) + 1,  # +1 for '@'
                        version_spec,
                        current_latest,
                        problem,
                        f"Fixed outdated version {version_spec} to latest {current_latest}",
                    )
                    action.uses_.string = f"{action_slug}@{current_latest}"
                yield problem

    def get_inputs(self, action: ExecAction) -> Union[Tuple[List[str], List[str]], Problem]:
        """
        Fetches metadata for an action and extracts its required and possible
        inputs.

        Args:
            action (ExecAction): The action to fetch inputs for.

        Returns:
            Tuple[List[str], List[str]]: Required and possible inputs if
                metadata is fetched successfully.
            Problem: Warning if metadata cannot be fetched.
        """
        action_metadata = parse_action(action.uses_.string)

        if action_metadata is None:
            return Problem(
                action.pos,
                ProblemLevel.WAR,
                (
                    f"Couldn't fetch metadata for {action.uses_.string}. "
                    "Continuing validation without"
                ),
                self.NAME,
            )

        inputs = action_metadata.get("inputs", {})
        possible_inputs = list(inputs.keys())
        required_inputs = [
            key
            for key, value in inputs.items()
            if (value.get("required") is True and value.get("default") is None)
        ]
        return required_inputs, possible_inputs

    def misses_required_input(
        self, action: ExecAction, required_inputs: list
    ) -> Generator[Problem, None, None]:
        """
        Checks if an action is missing any required inputs.

        Args:
            action (ExecAction): The action to validate.
            required_inputs (list): The list of required inputs.

        Yields:
            Problem: Error if required inputs are missing.
        """
        prettyprint_required_inputs = ", ".join(required_inputs)
        yield Problem(
            action.pos,
            ProblemLevel.ERR,
            (f"{action.uses_.string} requires inputs: " f"{prettyprint_required_inputs}"),
            self.NAME,
        )

    def check_required_inputs(self, action, required_inputs):
        """
        Validates that all required inputs for an action are provided.

        Args:
            action (ExecAction): The action to validate.
            required_inputs (list): The list of required inputs.

        Yields:
            Problem: Error if required inputs are missing.
        """
        if len(required_inputs) == 0:
            return

        for input in required_inputs:
            if input not in action.with_:
                yield from self.misses_required_input(action, required_inputs)

    def uses_non_defined_input(
        self, action: ExecAction, possible_inputs: List[str]
    ) -> Generator[Problem, None, None]:
        """
        Checks if an action uses inputs that are not defined in its metadata.

        Args:
            action (ExecAction): The action to validate.
            possible_inputs (List[str]): The list of possible inputs.

        Yields:
            Problem: Error if undefined inputs are used.
        """
        if len(possible_inputs) == 0:
            return

        for input in action.with_:
            if input not in possible_inputs:
                yield Problem(
                    action.pos,
                    ProblemLevel.ERR,
                    f"{action.uses_.string} uses unknown input: {input.string}",
                    self.NAME,
                )
