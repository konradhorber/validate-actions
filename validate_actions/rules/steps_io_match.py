from typing import Generator

from validate_actions import LintProblem
from validate_actions.rules import Rule
from validate_actions.workflow import Workflow


class StepsIOMatch(Rule):
    NAME = 'steps-io-match'
    
    @staticmethod
    def check(
        workflow: 'Workflow',
    ) -> Generator[LintProblem, None, None]:
        pass