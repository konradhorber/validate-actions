from typing import Dict, Generator

from validate_actions.lint_problem import LintProblem
from validate_actions.rules.rule import Rule
from validate_actions.rules.support_functions import parse_action
from validate_actions.workflow import Workflow, ast


class StepsIOMatch(Rule):
    NAME = 'steps-io-match'

    @staticmethod
    def check(
        workflow: 'Workflow',
    ) -> Generator[LintProblem, None, None]:
        jobs: Dict[ast.String, ast.Job] = workflow.jobs_
        for job in jobs.values():
            yield from StepsIOMatch.__check_job(job)

    @staticmethod
    def __check_job(job: ast.Job) -> Generator[LintProblem, None, None]:
        for step in job.steps_:
            yield from StepsIOMatch.__check_step_inputs(
                step,
                job,
            )

    @staticmethod
    def __check_step_inputs(
        step: ast.Step,
        job: ast.Job,
    ) -> Generator[LintProblem, None, None]:
        exec: ast.Exec = step.exec
        if not isinstance(exec, ast.ExecAction):
            return

        inputs: Dict[ast.String, ast.String] = exec.with_
        if len(inputs) == 0:
            return
        for input in inputs.values():
            if not isinstance(input, ast.Reference):
                continue

            section = input.parts[0]
            if section == 'env':
                pass
            elif section == 'secrets':
                pass
            elif section == 'jobs':
                pass
            elif section == 'steps':
                if len(input.parts) < 3:
                    yield LintProblem(
                        rule=StepsIOMatch.NAME,
                        desc=f'error in step reference {input.string}',
                        level='error',
                        pos=input.pos,
                    )
                    return
                yield from StepsIOMatch.__check_steps_ref_exists(input, job)
            else:
                yield LintProblem(
                    rule=StepsIOMatch.NAME,
                    desc=(
                        f"Step '{step.name_}' in job '{job.job_id_}' has an "
                        f"input '{input.string}' that does not match any step output"
                    ),
                    level='error',
                    pos=input.pos,
                )
        # TODO check if step produces correct outputs

    @staticmethod
    def __check_steps_ref_exists(
        ref: ast.Reference,
        job: ast.Job,
    ) -> Generator[LintProblem, None, None]:
        referenced_step_id = ref.parts[1]
        for step in job.steps_:
            if referenced_step_id == step.id_:
                yield from StepsIOMatch.__check_steps_ref_content(ref, step, job)
                return
        yield LintProblem(
            rule=StepsIOMatch.NAME,
            desc=(
                f"Step '{referenced_step_id}' in job '{job.job_id_}' does not exist"
            ),
            pos=ref.pos,
            level='error',
        )

    @staticmethod
    def __check_steps_ref_content(
        ref: ast.Reference,
        step: ast.Step,
        job: ast.Job,
    ) -> Generator[LintProblem, None, None]:
        if not isinstance(step.exec, ast.ExecAction):
            return  # TODO check for run exec type
        prev_step_metadata = parse_action(step.exec.uses_)

        ref_step_attr = ref.parts[2]  # e.g., outputs
        ref_step_var = ref.parts[3]
        if ref_step_attr in prev_step_metadata:
            type_: Dict[str, str] = prev_step_metadata[ref_step_attr]
            if type_ is None or len(type_) == 0:  # type is empty TODO check if none needed
                yield LintProblem(
                    rule=StepsIOMatch.NAME,
                    desc=(
                        f"'{ref.string}' refers to non-existent '{ref_step_attr}' in step "
                        f"'{step.name_}'"
                    ),
                    level='error',
                    pos=ref.pos,
                )
                return

            if ref_step_var not in type_.keys():  # e.g, id exists in outputs
                assert step.id_ is not None
                yield LintProblem(
                    rule=StepsIOMatch.NAME,
                    desc=f"'{ref_step_var}' not as '{ref_step_attr}' in '{step.id_.string}'",
                    level='error',
                    pos=ref.pos,
                )

        else:
            yield LintProblem(
                rule=StepsIOMatch.NAME,
                desc=f"'{ref_step_var}' does not exist in step '{step.name_}'",
                level='error',
                pos=ref.pos,
            )
