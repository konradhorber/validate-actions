from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Type

from validate_actions import rules
from validate_actions.fixer import BaseFixer
from validate_actions.job_orderer import JobOrderer
from validate_actions.problems import Problems
from validate_actions.rules.rule import Rule
from validate_actions.workflow.contexts import Contexts
from validate_actions.workflow.events_builder import EventsBuilder
from validate_actions.workflow.jobs_builder import JobsBuilder
from validate_actions.workflow.parser import PyYAMLParser
from validate_actions.workflow.steps_builder import StepsBuilder
from validate_actions.workflow.workflow_builder import WorkflowBuilder


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
        rules.JobsStepsUses,
        rules.StepsIOMatch,
        rules.ExpressionsContexts,
    ]

    @staticmethod
    def run(file: Path, fix: bool) -> Problems:
        problems: Problems = Problems()
        contexts = Contexts()
        events_builder = EventsBuilder(problems)
        steps_builder = StepsBuilder(problems, contexts)
        jobs_builder = JobsBuilder(problems, steps_builder, contexts)

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
        )

        workflow, problems = director.build()

        # Prepare workflow with job dependency analysis and needs contexts
        job_orderer = JobOrderer(problems)
        job_orderer.prepare_workflow(workflow)

        fixer = BaseFixer(file)

        jobs_steps_uses = rules.JobsStepsUses(workflow=workflow, fix=fix, fixer=fixer)
        steps_io_match = rules.StepsIOMatch(workflow=workflow, fix=fix, fixer=fixer)
        expressions_contexts = rules.ExpressionsContexts(workflow=workflow, fix=fix, fixer=fixer)

        cur_rules: List[Rule] = [jobs_steps_uses, steps_io_match, expressions_contexts]

        for rule in cur_rules:
            for problem in rule.check():
                problems.append(problem)

        # Apply all batched fixes if in fix mode
        if fix:
            fixer.flush()

        return problems
