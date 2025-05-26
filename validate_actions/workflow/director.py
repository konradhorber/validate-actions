from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import validate_actions.workflow.ast as ast
from validate_actions.pos import Pos
from validate_actions.problems import Problem, ProblemLevel, Problems
from validate_actions.workflow import helper
from validate_actions.workflow.events_builder import EventsBuilder
from validate_actions.workflow.jobs_builder import JobsBuilder
from validate_actions.workflow.parser import YAMLParser


class Director(ABC):
    @abstractmethod
    def build(self) -> Tuple[ast.Workflow, Problems]:
        """
        Build a structured workflow representation from the input YAML file.

        Returns:
            Tuple[Workflow, Problems]: A tuple containing the built
                Workflow object and a list of any lint problems found during
                parsing.
        """
        pass


class BaseDirector(Director):
    """
    Constructs a structured representation of a GitHub Actions workflow file.

    This class is responsible for parsing a GitHub Actions workflow YAML file
    and transforming it into a structured abstract syntax tree (AST)
    representation. It handles validation of the workflow structure during the
    parsing process and collects any problems encountered.
    """

    def __init__(
        self,
        workflow_file: Path,
        parser: YAMLParser,
        problems: Problems,
        events_builder: EventsBuilder,
        jobs_builder: JobsBuilder,
    ) -> None:
        """Initialize a WorkflowBuilder instance.

        Args:
            workflow_file (Path): Path to the workflow YAML file to be parsed
                and built.
            parser (YAMLParser): Parser instance used to parse the workflow
                YAML file.
            events_builder (EventsBuilder): Builder instance used to create
                events from the parsed data.
        """
        self.RULE_NAME = 'actions-syntax-error'
        self.workflow_file = workflow_file
        self.parser = parser
        self.problems = problems
        self.events_builder = events_builder
        self.jobs_builder = jobs_builder

    def build(self) -> Tuple[ast.Workflow, Problems]:
        """Parse the workflow file and build a structured workflow
        representation.

        This method processes the YAML file into a structured Workflow object,
        validating the structure and collecting any problems encountered.

        Returns:
            Tuple[Workflow, Problems]: A tuple containing the built
                Workflow object and a list of any lint problems found during
                parsing.
        """
        name_ = None
        run_name_ = None
        on_: List[ast.Event] = []
        permissions_ = ast.Permissions()
        env_: Optional[ast.Env] = None
        defaults_ = None
        concurrency_ = None
        jobs_: Dict[ast.String, ast.Job] = {}
        contexts = self.__init_contexts()

        # parse workflow yaml file
        workflow_dict, parser_problems = self.parser.parse(self.workflow_file)
        self.problems.extend(parser_problems)

        for key in workflow_dict:
            match key.string:
                case 'name':
                    name_ = workflow_dict[key].string
                case 'run-name':
                    run_name_ = workflow_dict[key].string
                case 'on':
                    on_ = self.events_builder.build(workflow_dict[key])
                case 'permissions':
                    permissions_ = helper.build_permissions(
                        workflow_dict[key], self.problems, self.RULE_NAME
                    )
                case 'env':
                    env_ = helper.build_env(workflow_dict[key], self.problems, self.RULE_NAME)
                case 'defaults':
                    defaults_ = self.__build_defaults(workflow_dict[key])
                case 'concurrency':
                    concurrency_ = self.__build_concurrency(workflow_dict[key])
                case 'jobs':
                    jobs_ = self.jobs_builder.build(workflow_dict[key])
                case _:
                    self.problems.append(Problem(
                        pos=key.pos,
                        desc=f"Unknown top-level workflow key: {key.string}",
                        level=ProblemLevel.ERR,
                        rule=self.RULE_NAME
                    ))
        if not on_ or not jobs_:
            self.problems.append(Problem(
                pos=Pos(0, 0),
                desc="Workflow must have at least one 'on' event and one job.",
                level=ProblemLevel.ERR,
                rule=self.RULE_NAME
            ))

        return ast.Workflow(
            on_=on_,
            jobs_=jobs_,
            name_=name_,
            run_name_=run_name_,
            permissions_=permissions_,
            env_=env_,
            defaults_=defaults_,
            concurrency_=concurrency_,
            contexts=contexts,
        ), self.problems

    def __build_defaults(
        self,
        workflow_dict: Dict[ast.String, Any]
    ) -> ast.Defaults:
        return ast.Defaults(None)

    def __build_concurrency(
        self, workflow_dict: Dict[ast.String, Any]
    ) -> ast.Concurrency:
        return ast.Concurrency(None)

    def __init_contexts(
        self
    ) -> Dict[str, ast.Context]:
        # A nested mapping of available contexts
        return {
            "github": ast.Context(
                type_="object",
                defined_=True,
                children_={
                    name: ast.Context(type_="string", defined_=True)
                    for name in [
                        "action",
                        "action_path",
                        "action_ref",
                        "action_repository",
                        "action_status",
                        "actor",
                        "actor_id",
                        "api_url",
                        "base_ref",
                        "env",
                        "event",
                        "event_name",
                        "event_path",
                        "graphql_url",
                        "head_ref",
                        "job",
                        "path",
                        "ref",
                        "ref_name",
                        "ref_protected",
                        "ref_type",
                        "repository",
                        "repository_id",
                        "repository_owner",
                        "repository_owner_id",
                        "repositoryUrl",
                        "retention_days",
                        "run_id",
                        "run_number",
                        "run_attempt",
                        "secret_source",
                        "server_url",
                        "sha",
                        "token",
                        "triggering_actor",
                        "workflow",
                        "workflow_ref",
                        "workflow_sha",
                        "workspace",
                    ]
                },
            ),
            "env": ast.Context(
                type_="object",
                defined_=True,
                children_={"<env_name>": ast.Context(type_="string", defined_=False)},
            ),
            "vars": ast.Context(
                type_="object",
                defined_=True,
                children_={"<var>": ast.Context(type_="string", defined_=False)},
            ),
            "job": ast.Context(
                type_="object",
                defined_=True,
                children_={
                    "container": ast.Context(
                        type_="object",
                        defined_=True,
                        children_={
                            "id": ast.Context(type_="string", defined_=True),
                            "network": ast.Context(type_="string", defined_=True),
                        },
                    ),
                    "services": ast.Context(
                        type_="object",
                        defined_=True,
                        children_={
                            "<service_id>": ast.Context(
                                type_="object",
                                defined_=True,
                                children_={
                                    "network": ast.Context(type_="string", defined_=True),
                                    "ports": ast.Context(type_="string", defined_=True),
                                },
                            )
                        },
                    ),
                    "status": ast.Context(type_="object", defined_=True, children_={}),
                },
            ),
            "jobs": ast.Context(
                type_="object",
                defined_=True,
                children_={
                    "<job_id>": ast.Context(
                        type_="object",
                        defined_=False,
                        children_={
                            "result": ast.Context(type_="string", defined_=False),
                            "outputs": ast.Context(
                                type_="object",
                                defined_=False,
                                children_={
                                    "<output_name>": ast.Context(type_="string", defined_=False)
                                },
                            ),
                        },
                    )
                },
            ),
            "steps": ast.Context(
                type_="object",
                defined_=True,
                children_={
                    "<step_id>": ast.Context(
                        type_="object",
                        defined_=False,
                        children_={
                            "outputs": ast.Context(
                                type_="object",
                                defined_=False,
                                children_={
                                    "<output_name>": ast.Context(type_="string", defined_=False)
                                },
                            ),
                            "conclusion": ast.Context(type_="string", defined_=False),
                            "outcome": ast.Context(type_="string", defined_=False),
                        },
                    )
                },
            ),
            "runner": ast.Context(
                type_="object",
                defined_=True,
                children_={
                    name: ast.Context(type_="string", defined_=True)
                    for name in [
                        "name",
                        "os",
                        "arch",
                        "temp",
                        "tool_cache",
                        "debug",
                        "environment",
                    ]
                },
            ),
            "secrets": ast.Context(
                type_="object",
                defined_=True,
                children_={
                    "GITHUB_TOKEN": ast.Context(type_="string", defined_=True),
                    "<secret_name>": ast.Context(type_="string", defined_=False),
                },
            ),
            "strategy": ast.Context(
                type_="object",
                defined_=True,
                children_={
                    flag: ast.Context(type_="string", defined_=True)
                    for flag in ["fail-fast", "job-index", "job-total", "max-parallel"]
                },
            ),
            "matrix": ast.Context(
                type_="object",
                defined_=True,
                children_={"<property_name>": ast.Context(type_="string", defined_=False)},
            ),
            "needs": ast.Context(
                type_="object",
                defined_=True,
                children_={
                    "<job_id>": ast.Context(
                        type_="object",
                        defined_=False,
                        children_={
                            "result": ast.Context(type_="string", defined_=False),
                            "outputs": ast.Context(
                                type_="object",
                                defined_=False,
                                children_={
                                    "<output_name>": ast.Context(type_="string", defined_=False)
                                },
                            ),
                        },
                    )
                },
            ),
            "inputs": ast.Context(
                type_="object",
                defined_=True,
                children_={"<input_name>": ast.Context(type_="string", defined_=False)},
            ),
        }
