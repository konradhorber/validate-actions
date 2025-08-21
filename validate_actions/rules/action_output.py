"""Validates step output references to previous steps in workflow expressions."""
from typing import Dict, Generator

from validate_actions.domain_model import ast
from validate_actions.domain_model.contexts import Contexts
from validate_actions.globals.problems import Problem, ProblemLevel
from validate_actions.rules.rule import Rule


class ActionOutput(Rule):
    """
    Validates step output references in workflow expressions.

    This rule ensures that when steps reference outputs from other steps using
    the `steps.<step-id>.outputs.<output-name>` syntax, both the step and the
    output exist and are accessible.
    """

    NAME = "action-output"

    def check(self) -> Generator[Problem, None, None]:
        """
        Check all jobs for invalid step output references.

        Yields:
            Problem: Issues with step output references
        """
        jobs: Dict[ast.String, ast.Job] = self.workflow.jobs_
        for job in jobs.values():
            yield from self.__check_job(job, contexts=self.workflow.contexts)

    def __check_job(self, job: ast.Job, contexts: Contexts) -> Generator[Problem, None, None]:
        """
        Check all steps in a job for invalid output references.

        Args:
            job: The job to check
            contexts: Workflow contexts for expression validation

        Yields:
            Problem: Issues with step output references in this job
        """
        for step in job.steps_:
            yield from self.__check_step_inputs(
                step,
                job,
                contexts,
            )

    def __check_step_inputs(
        self, step: ast.Step, job: ast.Job, contexts: Contexts
    ) -> Generator[Problem, None, None]:
        """
        Check step inputs for invalid output references.

        Args:
            step: The step to check
            job: The job containing this step
            contexts: Workflow contexts for expression validation

        Yields:
            Problem: Issues with step output references in step inputs
        """
        exec: ast.Exec = step.exec
        if not isinstance(exec, ast.ExecAction):
            return

        inputs: Dict[ast.String, ast.String] = exec.with_
        if len(inputs) == 0:
            return
        for input in inputs.values():
            if not isinstance(input, ast.String):
                continue
            if input.expr is None:
                continue

            for expr in input.expr:
                section = expr.parts[0]
                if section == "steps":
                    if len(expr.parts) < 3:
                        yield Problem(
                            rule=self.NAME,
                            desc=f"error in step expression {expr.string}",
                            level=ProblemLevel.ERR,
                            pos=input.pos,
                        )
                        return
                    yield from self.__check_steps_ref_exists(expr, job)

    def __check_steps_ref_exists(
        self,
        ref: ast.Expression,
        job: ast.Job,
    ) -> Generator[Problem, None, None]:
        """
        Check if the referenced step exists in the job.

        Args:
            ref: The expression referencing the step
            job: The job to search for the step

        Yields:
            Problem: Issues if the referenced step doesn't exist
        """
        referenced_step_id = ref.parts[1]
        for step in job.steps_:
            if referenced_step_id == step.id_:
                yield from self.__check_steps_ref_content(ref, step, job)
                return
        # Get available step IDs for suggestion
        available_steps = [step.id_.string for step in job.steps_ if step.id_]
        available_text = ""
        if available_steps:
            steps_list = "', '".join(available_steps)
            available_text = f" Available steps in this job: '{steps_list}'"

        yield Problem(
            rule=self.NAME,
            desc=(
                f"Step '{referenced_step_id.string}' in job '{job.job_id_}' "
                f"does not exist.{available_text}"
            ),
            pos=ref.pos,
            level=ProblemLevel.ERR,
        )

    def __check_steps_ref_content(
        self,
        ref: ast.Expression,
        step: ast.Step,
        job: ast.Job,
    ) -> Generator[Problem, None, None]:
        """
        Check if the referenced output exists in the step's action metadata.

        Args:
            ref: The expression referencing the step output
            step: The step being referenced
            job: The job containing the step

        Yields:
            Problem: Issues if the referenced output doesn't exist
        """
        if not isinstance(step.exec, ast.ExecAction):
            return

        # Use the new ActionMetadata if available
        if step.exec.metadata is None:
            return  # Unable to fetch action metadata

        try:
            ref_step_attr = ref.parts[2]  # e.g., outputs
            ref_step_var = ref.parts[3]
        except IndexError:
            yield Problem(
                rule=self.NAME,
                desc=f"Invalid reference '{ref.string}'",
                level=ProblemLevel.ERR,
                pos=ref.pos,
            )
            return

        # Check if we're looking for outputs
        if ref_step_attr.string == "outputs":
            outputs = step.exec.metadata.outputs
            if len(outputs) == 0:
                yield Problem(
                    rule=self.NAME,
                    desc=(f"'{ref.string}' refers to non-existent 'outputs' in step "),
                    level=ProblemLevel.ERR,
                    pos=ref.pos,
                )
                return

            if ref_step_var.string not in outputs.keys():
                assert step.id_ is not None
                yield Problem(
                    rule=self.NAME,
                    desc=(
                        f"'{ref_step_var.string}' not as "
                        f"'{ref_step_attr.string}' in '{step.id_.string}'"
                    ),
                    level=ProblemLevel.ERR,
                    pos=ref.pos,
                )

        else:
            # For non-outputs attributes, we don't have metadata yet
            # This could be extended for other attributes like inputs
            pass
