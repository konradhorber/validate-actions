from pathlib import Path
from typing import List, Type

from validate_actions import rules
from validate_actions.problems import Problems
from validate_actions.rules.rule import Rule
from validate_actions.workflow import helper
from validate_actions.workflow.contexts import Contexts
from validate_actions.workflow.director import BaseDirector
from validate_actions.workflow.events_builder import BaseEventsBuilder
from validate_actions.workflow.jobs_builder import BaseJobsBuilder
from validate_actions.workflow.parser import PyYAMLParser
from validate_actions.workflow.steps_builder import BaseStepsBuilder


class Validator:
    ACTIONS_ERROR_RULES: List[Type[Rule]] = [
        rules.JobsStepsUses,
        rules.StepsIOMatch,
        rules.ExpressionsContexts,
    ]

    @staticmethod
    def run(file: Path, fix: bool) -> Problems:
        workflow_schema = helper.get_workflow_schema('github-workflow.json')
        problems: Problems = Problems()
        contexts = Contexts()
        parser = PyYAMLParser()
        events_builder = BaseEventsBuilder(problems, workflow_schema)
        steps_builder = BaseStepsBuilder(problems, workflow_schema, contexts)
        jobs_builder = BaseJobsBuilder(problems, workflow_schema, steps_builder, contexts)
        director = BaseDirector(
            workflow_file=file,
            parser=parser,
            problems=problems,
            events_builder=events_builder,
            jobs_builder=jobs_builder,
            contexts=contexts,
        )

        workflow, problems = director.build()

        for rule in Validator.ACTIONS_ERROR_RULES:
            list_of_problems = rule.check(workflow, fix)
            for problem in list_of_problems:
                if problem is None:
                    continue
                problems.append(problem)

        return problems
