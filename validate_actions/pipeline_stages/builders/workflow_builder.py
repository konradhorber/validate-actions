"""Default implementation of a builder coordinating workflow construction."""
from typing import Any, Dict, List, Optional

import validate_actions.domain_model.ast as ast
from validate_actions.domain_model.contexts import Contexts
from validate_actions.domain_model.primitives import Pos, String
from validate_actions.globals.problems import Problem, ProblemLevel, Problems
from validate_actions.pipeline_stages.builders.events_builder import (
    DefaultEventsBuilder as EventsBuilder,
)
from validate_actions.pipeline_stages.builders.interfaces import (
    SharedComponentsBuilder,
    WorkflowBuilder,
)
from validate_actions.pipeline_stages.builders.jobs_builder import (
    DefaultJobsBuilder as JobsBuilder,
)


class DefaultWorkflowBuilder(WorkflowBuilder):
    """
    Constructs a structured representation of a GitHub Actions workflow file.

    This class is responsible for parsing a GitHub Actions workflow YAML file
    and transforming it into a structured abstract syntax tree (AST)
    representation. It handles validation of the workflow structure during the
    parsing process and collects any problems encountered.
    """

    def __init__(
        self,
        problems: Problems,
        events_builder: EventsBuilder,
        jobs_builder: JobsBuilder,
        contexts: Contexts,
        shared_components_builder: SharedComponentsBuilder,
    ) -> None:
        """Initialize a WorkflowBuilder instance.

        Args:
            problems (Problems): Problems collection to extend with any issues.
            events_builder (EventsBuilder): Builder instance used to create
                events from the parsed data.
            jobs_builder (JobsBuilder): Builder instance used to create
                jobs from the parsed data.
            contexts (Contexts): Contexts instance for workflow validation.
            shared_components_builder (ISharedComponentsBuilder): Builder for shared components.
        """
        super().__init__(problems)
        self.RULE_NAME = "actions-syntax-error"
        self.events_builder = events_builder
        self.jobs_builder = jobs_builder
        self.contexts = contexts
        self.shared_components_builder = shared_components_builder

    def process(self, workflow_dict: Dict[String, Any]) -> ast.Workflow:
        """Build a structured workflow representation from workflow dictionary.

        This method processes the workflow dictionary into a structured
        Workflow object, validating the structure and collecting any problems encountered.

        Args:
            workflow_dict (Dict[String, Any]): The workflow dictionary to process.

        Returns:
            ast.Workflow: The built Workflow object.
        """
        name_ = None
        run_name_ = None
        on_: List[ast.Event] = []
        permissions_ = ast.Permissions()
        env_: Optional[ast.Env] = None
        defaults_ = None
        concurrency_ = None
        jobs_: Dict[ast.String, ast.Job] = {}

        for key in workflow_dict:
            match key.string:
                case "name":
                    name_ = workflow_dict[key].string
                case "run-name":
                    run_name_ = workflow_dict[key].string
                case "on":
                    on_ = self.events_builder.build(workflow_dict[key])
                case "permissions":
                    permissions_ = self.shared_components_builder.build_permissions(
                        workflow_dict[key]
                    )
                case "env":
                    env_ = self.shared_components_builder.build_env(workflow_dict[key])
                case "defaults":
                    defaults_ = self.shared_components_builder.build_defaults(workflow_dict[key])
                case "concurrency":
                    concurrency_ = self.shared_components_builder.build_concurrency(
                        key, workflow_dict[key]
                    )
                case "jobs":
                    jobs_ = self.jobs_builder.build(workflow_dict[key])
                case _:
                    self.problems.append(
                        Problem(
                            pos=key.pos,
                            desc=f"Unknown top-level workflow key: {key.string}",
                            level=ProblemLevel.ERR,
                            rule=self.RULE_NAME,
                        )
                    )
        if not on_ or not jobs_:
            self.problems.append(
                Problem(
                    pos=Pos(0, 0),
                    desc="Workflow must have at least one 'on' event and one job.",
                    level=ProblemLevel.ERR,
                    rule=self.RULE_NAME,
                )
            )

        workflow = ast.Workflow(
            on_=on_,
            jobs_=jobs_,
            name_=name_,
            run_name_=run_name_,
            permissions_=permissions_,
            env_=env_,
            defaults_=defaults_,
            concurrency_=concurrency_,
            contexts=self.contexts,
        )

        return workflow
