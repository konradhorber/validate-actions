from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Type

from validate_actions import analyzing
from validate_actions.analyzing.rule import Rule
from validate_actions.building.events_builder import EventsBuilder
from validate_actions.building.jobs_builder import JobsBuilder
from validate_actions.building.shared_components_builder import SharedComponentsBuilder
from validate_actions.building.steps_builder import StepsBuilder
from validate_actions.building.workflow_builder import WorkflowBuilder
from validate_actions.core.problems import Problems
from validate_actions.domain_model.contexts import Contexts
from validate_actions.fixing.fixer import BaseFixer
from validate_actions.ordering.job_orderer import JobOrderer
from validate_actions.parsing.parser import PyYAMLParser


class IValidator(ABC):
    """
    Interface for Validator classes.

    Classes implementing this interface should provide a `run` method
    to validate workflow files and return problems found.
    """

    @staticmethod
    @abstractmethod
    def run(file: Path, fix: bool) -> Problems:
        """
        Validate a workflow file and return problems found.

        Args:
            file (Path): Path to the workflow file to validate.
            fix (bool): Whether to attempt automatic fixes for detected problems.

        Returns:
            Problems: A collection of problems found during validation.
        """
        pass


class Validator(IValidator):
    ACTIONS_ERROR_RULES: List[Type[Rule]] = [
        analyzing.JobsStepsUses,
        analyzing.StepsIOMatch,
        analyzing.ExpressionsContexts,
    ]

    @staticmethod
    def run(file: Path, fix: bool) -> Problems:
        problems: Problems = Problems()
        contexts = Contexts()
        shared_components_builder = SharedComponentsBuilder(problems)
        events_builder = EventsBuilder(problems)
        steps_builder = StepsBuilder(problems, contexts, shared_components_builder)
        jobs_builder = JobsBuilder(problems, steps_builder, contexts, shared_components_builder)

        # Parse the workflow file first
        parser = PyYAMLParser()
        workflow_dict, parser_problems = parser.parse(file)
        problems.extend(parser_problems)

        # Build workflow from parsed dict
        director = WorkflowBuilder(
            workflow_dict=workflow_dict,
            problems=problems,
            events_builder=events_builder,
            jobs_builder=jobs_builder,
            contexts=contexts,
            shared_components_builder=shared_components_builder,
        )

        workflow, problems = director.build()

        # Prepare workflow with job dependency analysis and needs contexts
        job_orderer = JobOrderer(problems)
        job_orderer.prepare_workflow(workflow)

        fixer = BaseFixer(file)

        jobs_steps_uses = analyzing.JobsStepsUses(workflow=workflow, fix=fix, fixer=fixer)
        steps_io_match = analyzing.StepsIOMatch(workflow=workflow, fix=fix, fixer=fixer)
        expressions_contexts = analyzing.ExpressionsContexts(
            workflow=workflow, fix=fix, fixer=fixer
        )

        cur_rules: List[Rule] = [jobs_steps_uses, steps_io_match, expressions_contexts]

        for rule in cur_rules:
            for problem in rule.check():
                problems.append(problem)

        # Apply all batched fixes if in fix mode
        if fix:
            fixer.flush()

        return problems
