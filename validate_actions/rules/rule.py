from abc import ABC, abstractmethod
from typing import Generator

from validate_actions.lint_problem import LintProblem
from validate_actions.workflow.ast import Workflow


class Rule(ABC):

    @staticmethod
    @abstractmethod
    def check(
        workflow: Workflow
    ) -> Generator[LintProblem, None, None]:
        """
        Perform checks on the given workflow and schema, yielding LintProblem]
        instances.
        """
        pass
