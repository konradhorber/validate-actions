from pathlib import Path
from typing import List

from validate_actions import rules
from validate_actions.lint_problem import LintProblem
from validate_actions.workflow.director import BaseDirector
from validate_actions.workflow.events_builder import BaseEventsBuilder
from validate_actions.workflow.jobs_builder import BaseJobsBuilder
from validate_actions.workflow.parser import PyYAMLParser

PROBLEM_LEVELS = {
    0: None,
    1: 'warning',
    2: 'error',
    None: 0,
    'warning': 1,
    'error': 2,
}


def run(file: Path) -> List[LintProblem]:
    problems: List[LintProblem] = []
    builder = BaseDirector(
        workflow_file=file,
        parser=PyYAMLParser(),
        problems=problems,
        events_builder=BaseEventsBuilder(problems=problems),
        jobs_builder=BaseJobsBuilder(problems=problems),
    )
    workflow, problems = builder.build()

    for rule in ACTIONS_ERROR_RULES:
        problems.extend(rule.check(workflow))

    # TODO fix this mess
    for problem in problems:
        if problem is None:
            problems.remove(problem)
    return problems


ACTIONS_ERROR_RULES = [
    rules.JobsStepsUses
    ]
