"""Validates input specifications in workflow action 'uses:' fields."""
from typing import Generator, List

from validate_actions.domain_model.ast import ExecAction
from validate_actions.globals.problems import Problem, ProblemLevel
from validate_actions.rules.rule import Rule


class ActionInput(Rule):
    """Validates input specifications in workflow action 'uses:' fields.

    This rule checks GitHub Actions workflow steps that reference external actions
    via the 'uses:' field. It validates input specifications to ensure proper
    action configuration.

    Key validations:
    - Validates required inputs are provided
    - Checks that only defined inputs are used
    """

    NAME = "action-input"

    # ====================
    # MAIN VALIDATION METHODS
    # ====================

    def check(self) -> Generator[Problem, None, None]:
        """Validates all actions in the workflow for input issues.

        Iterates through all workflow jobs and their steps, collecting
        ExecAction instances (steps that use the 'uses:' field) and
        validates them for input requirements.

        Yields:
            Problem: Problems found during validation including missing inputs
                and usage of undefined inputs.
        """
        actions = []
        for job in self.workflow.jobs_.values():
            steps = job.steps_
            for step in steps:
                if isinstance(step.exec, ExecAction):
                    actions.append(step.exec)
        return self._check_single_action(actions)

    def _check_single_action(
        self,
        actions: List[ExecAction],
    ) -> Generator[Problem, None, None]:
        """Validates each action individually for input issues.

        Processes each ExecAction to validate input requirements against
        the action's metadata (if available).

        Args:
            actions: List of ExecAction instances to validate.

        Yields:
            Problem: Problems found including missing required inputs
                and usage of undefined inputs.
        """
        for action in actions:
            required_inputs = action.metadata.required_inputs if action.metadata else []
            possible_inputs = action.metadata.possible_inputs if action.metadata else []

            if len(action.with_) == 0:
                if len(required_inputs) == 0:
                    continue
                else:
                    yield from self._misses_required_input(action, required_inputs)
            else:
                yield from self._check_required_inputs(action, required_inputs)
                yield from self._uses_non_defined_input(action, possible_inputs)

    # ====================
    # INPUT VALIDATION METHODS
    # ====================

    def _misses_required_input(
        self, action: ExecAction, required_inputs: List[str]
    ) -> Generator[Problem, None, None]:
        """Generates an error problem for missing required inputs.

        This is a helper method that creates a formatted error message
        listing all required inputs for an action.

        Args:
            action: The action missing required inputs.
            required_inputs: List of all required input names.

        Yields:
            Problem: Error problem with formatted list of required inputs.
        """
        prettyprint_required_inputs = ", ".join(required_inputs)
        yield Problem(
            action.pos,
            ProblemLevel.ERR,
            (f"{action.uses_.string} requires inputs: " f"{prettyprint_required_inputs}"),
            self.NAME,
        )

    def _check_required_inputs(
        self, action: ExecAction, required_inputs: List[str]
    ) -> Generator[Problem, None, None]:
        """Validates that all required inputs for an action are provided.

        Iterates through all required inputs and checks if they are present
        in the action's 'with:' section. Generates problems for missing inputs.

        Args:
            action: The action to validate.
            required_inputs: List of required input names for this action.

        Yields:
            Problem: Error problems for each missing required input.
        """
        if not required_inputs:
            return

        for required_input in required_inputs:
            if required_input not in action.with_:
                yield from self._misses_required_input(action, required_inputs)

    def _uses_non_defined_input(
        self, action: ExecAction, possible_inputs: List[str]
    ) -> Generator[Problem, None, None]:
        """
        Checks if an action uses inputs that are not defined in its metadata.

        Args:
            action (ExecAction): The action to validate.
            possible_inputs (List[str]): The list of possible inputs.

        Yields:
            Problem: Error if undefined inputs are used.
        """
        if not possible_inputs:
            return

        for action_input in action.with_:
            if action_input not in possible_inputs:
                yield Problem(
                    action.pos,
                    ProblemLevel.ERR,
                    f"{action.uses_.string} uses unknown input: {action_input.string}",
                    self.NAME,
                )
