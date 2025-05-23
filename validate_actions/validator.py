from pathlib import Path

from validate_actions import rules
from validate_actions.problems import Problems
from validate_actions.workflow import helper
from validate_actions.workflow.director import BaseDirector
from validate_actions.workflow.events_builder import BaseEventsBuilder
from validate_actions.workflow.jobs_builder import BaseJobsBuilder
from validate_actions.workflow.parser import PyYAMLParser


class Validator:
    ACTIONS_ERROR_RULES = [
        rules.JobsStepsUses
    ]

    @staticmethod
    def run(file: Path) -> Problems:
        workflow_schema = helper.get_workflow_schema('github-workflow.json')
        problems: Problems = Problems()
        parser = PyYAMLParser()
        events_builder = BaseEventsBuilder(problems, workflow_schema)
        jobs_builder = BaseJobsBuilder(problems, workflow_schema)
        director = BaseDirector(
            workflow_file=file,
            parser=parser,
            problems=problems,
            events_builder=events_builder,
            jobs_builder=jobs_builder,
        )

        workflow, problems = director.build()

        for rule in Validator.ACTIONS_ERROR_RULES:
            list_of_problems = rule.check(workflow)
            for problem in list_of_problems:
                if problem is None:
                    continue
                problems.append(problem)

        return problems
