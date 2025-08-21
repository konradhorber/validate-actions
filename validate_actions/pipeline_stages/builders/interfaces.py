"""Interfaces for support builders."""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union

from validate_actions.domain_model import ast
from validate_actions.domain_model.contexts import Contexts
from validate_actions.globals.process_stage import ProcessStage


class SharedComponentsBuilder(ABC):
    """Builder interface for shared attributes on varying levels (workflow, job, step)."""
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


class EventsBuilder(ABC):
    """Builder interface for events (after on keyword in workflow file). Builds
    from parsed workflow data. Doens't parse the file.
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


class StepsBuilder(ABC):
    """
    Builder for steps in a GitHub Actions workflow.
    Converts a list of step definitions into a list of Step objects.
    """

    @abstractmethod
    def build(
        self, steps_in: List[Dict[ast.String, Any]], local_contexts: Contexts
    ) -> List[ast.Step]:
        pass


class JobsBuilder(ABC):
    """Builder interface for jobs."""
    @abstractmethod
    def build(self, jobs_dict: Dict[ast.String, Any]) -> Dict[ast.String, ast.Job]:
        """
        Build events from the input data.
        """
        pass


class WorkflowBuilder(ProcessStage[Dict[ast.String, Any], ast.Workflow]):
    """Builder interface for whole workflow construction from other builders."""
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
