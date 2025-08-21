"""Interface for GitHub Actions workflow validation rules."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Generator

from validate_actions.domain_model.ast import Workflow
from validate_actions.globals.fixer import Fixer
from validate_actions.globals.problems import Problem


class Rule(ABC):
    """Base class for all GitHub Actions workflow validation rules.

    Rules examine workflows for specific issues and can optionally fix them
    automatically. Each rule operates on a workflow AST and yields Problem
    instances for any issues found.

    The rule system supports both validation-only and auto-fixing modes,
    controlled by the fixer implementation provided during initialization.

    Attributes:
        workflow: The workflow AST to validate
        fixer: Fixer instance for making automatic corrections

    Examples:
        Creating a custom rule:
            class MyRule(Rule):
                def check(self) -> Generator[Problem, None, None]:
                    if some_condition:
                        yield Problem(pos, ProblemLevel.ERR, "Error message", "rule-name")

        Using a rule:
            rule = MyRule(workflow, fixer)
            problems = list(rule.check())
    """

    def __init__(self, workflow: Workflow, fixer: Fixer) -> None:
        """Initialize the rule with a workflow and fixer instance.

        Args:
            workflow: The workflow AST to validate
            fixer: Fixer instance for automatic corrections. Can be a NoFixer
                implementation that does nothing when validation-only mode is desired.
        """
        self.workflow = workflow
        self.fixer = fixer

    @abstractmethod
    def check(self) -> Generator[Problem, None, None]:
        """Perform validation checks on the workflow.

        Examines the workflow for rule-specific issues and yields Problem
        instances for any violations found. May also apply automatic fixes
        through the fixer if enabled.

        Yields:
            Problem: Validation issues found, with position, level, description,
                and rule name information.
        """
        pass
