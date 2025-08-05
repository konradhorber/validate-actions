from typing import Dict, Generator

from validate_actions.analyzing.rule import Rule
from validate_actions.analyzing.support_functions import parse_action
from validate_actions.core.problems import Problem, ProblemLevel
from validate_actions.domain_model import ast
from validate_actions.domain_model.contexts import Contexts


class StepsIOMatch(Rule):
    NAME = "steps-io-match"

    def check(self) -> Generator[Problem, None, None]:
        jobs: Dict[ast.String, ast.Job] = self.workflow.jobs_
        for job in jobs.values():
            yield from self.__check_job(job, contexts=self.workflow.contexts)

    def __check_job(self, job: ast.Job, contexts: Contexts) -> Generator[Problem, None, None]:
        for step in job.steps_:
            yield from self.__check_step_inputs(
                step,
                job,
                contexts,
            )

    def __check_step_inputs(
        self, step: ast.Step, job: ast.Job, contexts: Contexts
    ) -> Generator[Problem, None, None]:
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
        if not isinstance(step.exec, ast.ExecAction):
            return  # TODO check for run exec type
        prev_step_metadata = parse_action(step.exec.uses_)
        if prev_step_metadata is None:
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

        if ref_step_attr in prev_step_metadata:
            type_: Dict[str, str] = prev_step_metadata[ref_step_attr]
            if type_ is None or len(type_) == 0:  # type is empty TODO check if none needed
                yield Problem(
                    rule=self.NAME,
                    desc=(
                        f"'{ref.string}' refers to non-existent '{ref_step_attr.string}' in step "
                    ),
                    level=ProblemLevel.ERR,
                    pos=ref.pos,
                )
                return

            if ref_step_var not in type_.keys():  # e.g, id exists in outputs
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
            yield Problem(
                rule=self.NAME,
                desc=f"'{ref_step_var.string}' does not exist in step",
                level=ProblemLevel.ERR,
                pos=ref.pos,
            )
