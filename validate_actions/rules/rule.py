from abc import ABC, abstractmethod
from validate_actions.workflow.ast import Workflow
from validate_actions.lint_problem import LintProblem
from validate_actions.workflow.ast import String
from typing import Optional, Generator, Dict, Any


class Rule(ABC):

    @staticmethod
    @abstractmethod
    def check(
        workflow: Workflow, 
        schema: Optional[Dict[String, Any]] = None
    ) -> Generator[LintProblem, None, None]:
        """
        Perform checks on the given workflow and schema, yielding LintProblem]
        instances.
        """
        pass
