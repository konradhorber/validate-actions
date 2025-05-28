from typing import Any, Dict, Generator, List, Optional, Tuple, Union

from validate_actions.problems import Problem, ProblemLevel
from validate_actions.rules.rule import Rule
from validate_actions.rules.support_functions import parse_action
from validate_actions.workflow.ast import ExecAction, String, Workflow


class JobsStepsUses(Rule):
    """
    Validates the `uses:` field in workflow steps.
    """

    NAME = 'jobs-steps-uses'

    @staticmethod
    def check(
        workflow: 'Workflow',
    ) -> Generator[Problem, None, None]:
        """
        Validates all actions in the workflow.

        Args:
            workflow (Workflow): The workflow to validate.
            schema (dict, optional): The schema to validate against. Defaults
                to None.

        Yields:
            Problem: Problems found during validation.
        """
        return JobsStepsUses.check_single_action(workflow)

    @staticmethod
    def check_single_action(
        workflow: 'Workflow'
    ) -> Generator[Problem, None, None]:
        """
        Validates actions individually without context declared by `uses:` in
        the workflow steps.

        Args:
            workflow (Workflow): The workflow to validate.

        Yields:
            Problem: Problems found during validation.
        """
        actions = []
        for job in workflow.jobs_.values():
            steps = job.steps_
            for step in steps:
                if isinstance(step.exec, ExecAction):
                    actions.append(step.exec)

        for action in actions:
            yield from JobsStepsUses.not_using_version_spec(action)
            input_result = JobsStepsUses.get_inputs(action)
            if isinstance(input_result, Problem):
                yield input_result
                return
            else:
                required_inputs, possible_inputs = input_result

            if len(action.with_) == 0:
                if len(required_inputs) == 0:
                    continue
                else:
                    yield from JobsStepsUses.misses_required_input(
                        action, required_inputs
                    )
            else:
                yield from JobsStepsUses.check_required_inputs(
                    action, required_inputs
                )
                yield from JobsStepsUses.uses_non_defined_input(
                    action, possible_inputs
                )

    @staticmethod
    def not_using_version_spec(
        action: ExecAction,
    ) -> Generator[Problem, None, None]:
        """
        Checks if an action specifies a version using `@version`. If not, a
        warning is generated.

        Args:
            action (ExecAction): The action to validate.

        Yields:
            Problem: Warning if version is not specified.
        """
        if '@' not in action.uses_.string:
            yield Problem(
                    action.pos,
                    ProblemLevel.WAR,
                    (
                        f'Using specific version of {action.uses_.string} is '
                        f'recommended @version'
                    ),
                    JobsStepsUses.NAME
                )

    @staticmethod
    def get_inputs(
        action: ExecAction
    ) -> Union[Tuple[List[str], List[str]], Problem]:
        """
        Fetches metadata for an action and extracts its required and possible
        inputs.

        Args:
            action (ExecAction): The action to fetch inputs for.

        Returns:
            Tuple[List[str], List[str]]: Required and possible inputs if
                metadata is fetched successfully.
            Problem: Warning if metadata cannot be fetched.
        """
        action_metadata = parse_action(action.uses_.string)

        if action_metadata is None:
            return Problem(
                action.pos,
                ProblemLevel.WAR,
                (
                    f"Couldn't fetch metadata for {action.uses_.string}. "
                    "Continuing validation without"
                ),
                JobsStepsUses.NAME
            )

        inputs = action_metadata['inputs']
        possible_inputs = list(inputs.keys())
        required_inputs = [
            key for key, value in inputs.items()
            if value.get('required') is True
        ]
        return required_inputs, possible_inputs

    @staticmethod
    def misses_required_input(
        action: ExecAction,
        required_inputs: list
    ) -> Generator[Problem, None, None]:
        """
        Checks if an action is missing any required inputs.

        Args:
            action (ExecAction): The action to validate.
            required_inputs (list): The list of required inputs.

        Yields:
            Problem: Error if required inputs are missing.
        """
        prettyprint_required_inputs = ', '.join(required_inputs)
        yield Problem(
            action.pos,
            ProblemLevel.ERR,
            (
                f'{action.uses_.string} requires inputs: '
                f'{prettyprint_required_inputs}'
            ),
            JobsStepsUses.NAME
        )

    @staticmethod
    def check_required_inputs(action, required_inputs):
        """
        Validates that all required inputs for an action are provided.

        Args:
            action (ExecAction): The action to validate.
            required_inputs (list): The list of required inputs.

        Yields:
            Problem: Error if required inputs are missing.
        """
        if len(required_inputs) == 0:
            return

        for input in required_inputs:
            if input not in action.with_:
                yield from JobsStepsUses.misses_required_input(
                    action, required_inputs
                )

    @staticmethod
    def uses_non_defined_input(
        action: ExecAction,
        possible_inputs: List[str]
    ) -> Generator[Problem, None, None]:
        """
        Checks if an action uses inputs that are not defined in its metadata.

        Args:
            action (ExecAction): The action to validate.
            possible_inputs (List[str]): The list of possible inputs.

        Yields:
            Problem: Error if undefined inputs are used.
        """
        if len(possible_inputs) == 0:
            return

        for input in action.with_:
            if input not in possible_inputs:
                yield Problem(
                    action.pos,
                    ProblemLevel.ERR,
                    f'{action.uses_.string} uses unknown input: {input.string}',
                    JobsStepsUses.NAME
                )
