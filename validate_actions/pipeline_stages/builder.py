from abc import abstractmethod
from typing import Any, Dict

import validate_actions.domain_model.ast as ast
from validate_actions.domain_model.contexts import Contexts
from validate_actions.globals.problems import Problems
from validate_actions.globals.process_stage import ProcessStage
from validate_actions.pipeline_stages.builders.events_builder import EventsBuilder
from validate_actions.pipeline_stages.builders.jobs_builder import JobsBuilder
from validate_actions.pipeline_stages.builders.shared_components_builder import (
    SharedComponentsBuilder,
)
from validate_actions.pipeline_stages.builders.steps_builder import StepsBuilder
from validate_actions.pipeline_stages.builders.workflow_builder import WorkflowBuilder


class IBuilder(ProcessStage[Dict[ast.String, Any], ast.Workflow]):
    @abstractmethod
    def process(self, workflow_dict: Dict[ast.String, Any]) -> ast.Workflow:
        pass


class Builder(IBuilder):
    def __init__(self, problems: Problems) -> None:
        super().__init__(problems)

        contexts = Contexts()
        self.shared_components_builder = SharedComponentsBuilder(problems)
        self.events_builder = EventsBuilder(problems)
        self.steps_builder = StepsBuilder(problems, contexts, self.shared_components_builder)
        self.jobs_builder = JobsBuilder(
            problems, self.steps_builder, contexts, self.shared_components_builder
        )

        self.workflow_builder = WorkflowBuilder(
            problems=problems,
            events_builder=self.events_builder,
            jobs_builder=self.jobs_builder,
            contexts=contexts,
            shared_components_builder=self.shared_components_builder,
        )

    def process(self, workflow_dict: Dict[ast.String, Any]) -> ast.Workflow:
        return self.workflow_builder.process(workflow_dict)
