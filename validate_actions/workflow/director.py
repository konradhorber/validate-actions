from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import validate_actions.workflow.ast as ast
from validate_actions.pos import Pos
from validate_actions.problems import Problem, ProblemLevel, Problems
from validate_actions.workflow import helper
from validate_actions.workflow.contexts import Contexts
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
        contexts: Contexts,
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
        self.contexts = contexts

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
                    env_ = helper.build_env(
                        workflow_dict[key], self.contexts, self.problems, self.RULE_NAME
                    )
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
            path=self.workflow_file,
            on_=on_,
            jobs_=jobs_,
            name_=name_,
            run_name_=run_name_,
            permissions_=permissions_,
            env_=env_,
            defaults_=defaults_,
            concurrency_=concurrency_,
            contexts=self.contexts,
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
