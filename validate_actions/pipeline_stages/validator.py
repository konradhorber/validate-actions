from abc import abstractmethod
from typing import List, Optional

from validate_actions.domain_model import ast
from validate_actions.globals.fixer import Fixer
from validate_actions.globals.problems import Problems
from validate_actions.globals.process_stage import ProcessStage
from validate_actions.rules.expressions_contexts import ExpressionsContexts
from validate_actions.rules.jobs_steps_uses import JobsStepsUses
from validate_actions.rules.rule import Rule
from validate_actions.rules.steps_io_match import StepsIOMatch


class IValidator(ProcessStage[ast.Workflow, Problems]):
    @abstractmethod
    def process(self, workflow: ast.Workflow) -> Problems:
        """Validate the given workflow and return any problems found.

        Args:
            workflow: The workflow to validate.

        Returns:
            A Problems object containing any issues found during validation.
        """
        pass


class Validator(IValidator):
    def __init__(self, problems: Problems, fixer: Optional[Fixer] = None) -> None:
        super().__init__(problems)
        self.fixer = fixer

    def process(self, workflow: ast.Workflow) -> Problems:
        """Validate the given workflow and return any problems found.

        Args:
            workflow: The workflow to validate.

        Returns:
            A Problems object containing any issues found during validation.
        """
        if self.fixer is None:
            fix = False
        else:
            fix = True
        jobs_steps_uses = JobsStepsUses(workflow=workflow, fix=fix, fixer=self.fixer)
        steps_io_match = StepsIOMatch(workflow=workflow, fix=fix, fixer=self.fixer)
        expressions_contexts = ExpressionsContexts(workflow=workflow, fix=fix, fixer=self.fixer)

        cur_rules: List[Rule] = [jobs_steps_uses, steps_io_match, expressions_contexts]

        for rule in cur_rules:
            for problem in rule.check():
                self.problems.append(problem)

        # Apply all batched fixes if in fix mode
        if fix and self.fixer is not None:
            self.fixer.flush()
        return self.problems
