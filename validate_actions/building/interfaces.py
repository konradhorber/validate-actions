from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union

from validate_actions.core.interfaces import ProcessStage
from validate_actions.domain_model import ast
from validate_actions.domain_model.contexts import Contexts


class ISharedComponentsBuilder(ABC):
    @abstractmethod
    def build_env(self, env_vars: Dict[ast.String, Any]) -> Optional[ast.Env]:
        """Build environment variables from dictionary."""
        pass

    @abstractmethod
    def build_permissions(
        self, permissions_in: Union[Dict[ast.String, Any], ast.String]
    ) -> ast.Permissions:
        """Build permissions from input data."""
        pass

    @abstractmethod
    def build_defaults(
        self, defaults_dict: Dict[ast.String, Dict[ast.String, Dict[ast.String, ast.String]]]
    ) -> Optional[ast.Defaults]:
        """Build defaults from dictionary."""
        pass

    @abstractmethod
    def build_concurrency(
        self,
        key: ast.String,
        concurrency_in: Dict[ast.String | str, ast.String],
    ) -> Optional[ast.Concurrency]:
        """Build concurrency configuration."""
        pass


class IEventsBuilder(ABC):
    """Builder interface for events (after on keyword in workflow file). Builds
    from parsed workflow data. Doens't parse the file.

    Args:
        ABC (_type_): is an interface
    """

    @abstractmethod
    def build(
        self, events_in: Union[ast.String, Dict[ast.String, Any], List[Any]]
    ) -> List[ast.Event]:
        """Build events from the given input.

        Args:
            events_in (Union[ast.String, Dict[ast.String, Any], List[Any]]):
                Input data representing the events. Starts after the on:
                keyword in the workflow file.


        Returns:
            List[ast.Event]: A list of events built.
        """
        pass


class IWorkflowBuilder(ProcessStage[Dict[ast.String, Any], ast.Workflow]):
    @abstractmethod
    def process(self, workflow_dict: Dict[ast.String, Any]) -> ast.Workflow:
        """
        Build a structured workflow representation from the input dictionary.

        Args:
            workflow_dict: Parsed workflow dictionary to build from

        Returns:
            ast.Workflow: The built Workflow object.
        """
        pass


class IJobsBuilder(ABC):
    @abstractmethod
    def build(self, jobs_dict: Dict[ast.String, Any]) -> Dict[ast.String, ast.Job]:
        """
        Build events from the input data.
        """
        pass


class IStepsBuilder(ABC):
    """
    Builder for steps in a GitHub Actions workflow.
    Converts a list of step definitions into a list of Step objects.
    """

    @abstractmethod
    def build(
        self, steps_in: List[Dict[ast.String, Any]], local_contexts: Contexts
    ) -> List[ast.Step]:
        pass


class IMarketPlaceEnricher(ProcessStage[ast.Workflow, ast.Workflow]):
    """Interface for enriching workflows with marketplace metadata.

    Fetches action metadata from GitHub marketplace/repositories to enrich
    workflow AST with action input/output information and version data.
    """

    @abstractmethod
    def process(self, workflow: ast.Workflow) -> ast.Workflow:
        """Enrich workflow with marketplace metadata.

        Args:
            workflow: The workflow to enrich with marketplace data

        Returns:
            ast.Workflow: The enriched workflow with metadata attached to actions
        """
        pass


class IJobOrderer(ProcessStage[ast.Workflow, ast.Workflow]):
    """Interface for job ordering and dependency analysis."""

    @abstractmethod
    def process(self, workflow: ast.Workflow) -> ast.Workflow:
        """Process workflow with job dependency analysis and needs contexts.

        Args:
            workflow: The workflow to analyze and enrich with job ordering

        Returns:
            ast.Workflow: The workflow with job dependency analysis completed
        """
        pass
