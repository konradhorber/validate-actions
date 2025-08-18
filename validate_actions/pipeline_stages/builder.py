from abc import abstractmethod
from typing import Any, Dict

from validate_actions.domain_model.ast import Workflow
from validate_actions.domain_model.contexts import Contexts
from validate_actions.domain_model.primitives import String
from validate_actions.globals.problems import Problems
from validate_actions.globals.process_stage import ProcessStage
from validate_actions.pipeline_stages.builders.events_builder import DefaultEventsBuilder
from validate_actions.pipeline_stages.builders.jobs_builder import DefaultJobsBuilder
from validate_actions.pipeline_stages.builders.shared_components_builder import (
    DefaultSharedComponentsBuilder,
)
from validate_actions.pipeline_stages.builders.steps_builder import DefaultStepsBuilder
from validate_actions.pipeline_stages.builders.workflow_builder import DefaultWorkflowBuilder


class Builder(ProcessStage[Dict[String, Any], Workflow]):
    """Abstract base class for workflow AST builders.

    The Builder stage transforms parsed YAML data into a structured AST
    representation that can be used for validation and analysis.
    """

    @abstractmethod
    def process(self, workflow_dict: Dict[String, Any]) -> Workflow:
        """Build a workflow AST from parsed YAML data.

        Args:
            workflow_dict: Dictionary representation of the parsed workflow YAML,
                         with String keys preserving position information

        Returns:
            Workflow: Complete AST representation of the GitHub Actions workflow
        """
        pass


class DefaultBuilder(Builder):
    def __init__(self, problems: Problems) -> None:
        super().__init__(problems)

        contexts = Contexts()
        self.shared_components_builder = DefaultSharedComponentsBuilder(problems)
        self.events_builder = DefaultEventsBuilder(problems)
        self.steps_builder = DefaultStepsBuilder(
            problems, contexts, self.shared_components_builder
        )
        self.jobs_builder = DefaultJobsBuilder(
            problems, self.steps_builder, contexts, self.shared_components_builder
        )

        self.workflow_builder = DefaultWorkflowBuilder(
            problems=problems,
            events_builder=self.events_builder,
            jobs_builder=self.jobs_builder,
            contexts=contexts,
            shared_components_builder=self.shared_components_builder,
        )

    def process(self, workflow_dict: Dict[String, Any]) -> Workflow:
        return self.workflow_builder.process(workflow_dict)
