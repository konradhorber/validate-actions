from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Generator

from validate_actions.domain_model.ast import Workflow
from validate_actions.globals.fixer import Fixer
from validate_actions.globals.problems import Problem


class Rule(ABC):
    def __init__(self, workflow: Workflow, fixer: Fixer) -> None:
        """
        Initialize the rule with a fixer instance.
        The fixer can be a NoFixer implementation that does nothing
        when validation-only mode is desired.
        """
        self.workflow = workflow
        self.fixer = fixer

    @abstractmethod
    def check(
        self,
    ) -> Generator[Problem, None, None]:
        """
        Perform checks on the given workflow and schema, yielding Problem
        instances.
        """
        pass
