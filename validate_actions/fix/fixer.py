from pathlib import Path

from validate_actions.problems import Problem
from validate_actions.workflow.ast import Workflow


class Fixer:
    @staticmethod
    def fix(problem: Problem, workflow: Workflow, file: Path) -> bool:
        return False
