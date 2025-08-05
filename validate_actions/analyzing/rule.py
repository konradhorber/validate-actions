from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Generator

from validate_actions.core.problems import Problem
from validate_actions.domain_model.ast import Workflow
from validate_actions.fixing.fixer import Fixer


class Rule(ABC):
    def __init__(self, workflow: Workflow, fix: bool, fixer: Fixer):
        """
        Initialize the rule with a flag indicating whether to fix issues
        and an optional fixer instance.
        """
        self.workflow = workflow
        self.fix = fix
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
