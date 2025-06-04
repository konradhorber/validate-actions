from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Generator

if TYPE_CHECKING:
    from validate_actions.problems import Problem
    from validate_actions.workflow.ast import Workflow


class Rule(ABC):

    @staticmethod
    @abstractmethod
    def check(
        workflow: Workflow,
        fix: bool,
    ) -> Generator[Problem, None, None]:
        """
        Perform checks on the given workflow and schema, yielding Problem
        instances.
        """
        pass
