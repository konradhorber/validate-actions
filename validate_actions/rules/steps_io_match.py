from typing import Dict, Generator

from validate_actions.problems import Problem, ProblemLevel
from validate_actions.rules.rule import Rule
from validate_actions.rules.support_functions import parse_action
from validate_actions.workflow import Workflow, ast
from validate_actions.workflow.contexts import Contexts


class StepsIOMatch(Rule):
    NAME = 'steps-io-match'

    @staticmethod
    def check(
        workflow: 'Workflow',
        fix: bool
    ) -> Generator[Problem, None, None]:
        jobs: Dict[ast.String, ast.Job] = workflow.jobs_
        for job in jobs.values():
            yield from StepsIOMatch.__check_job(job, contexts=workflow.contexts)

    @staticmethod
    def __check_job(job: ast.Job, contexts: Contexts) -> Generator[Problem, None, None]:
        for step in job.steps_:
            yield from StepsIOMatch.__check_step_inputs(
                step,
                job,
                contexts,
            )

    @staticmethod
    def __check_step_inputs(
        step: ast.Step,
        job: ast.Job,
        contexts: Contexts
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

            section = input.expr.parts[0]
            if section == 'steps':
                if len(input.expr.parts) < 3:
                    yield Problem(
                        rule=StepsIOMatch.NAME,
                        desc=f'error in step expression {input.expr.string}',
                        level=ProblemLevel.ERR,
                        pos=input.pos,
                    )
                    return
                yield from StepsIOMatch.__check_steps_ref_exists(input.expr, job)

    @staticmethod
    def __check_steps_ref_exists(
        ref: ast.Expression,
        job: ast.Job,
    ) -> Generator[Problem, None, None]:
        referenced_step_id = ref.parts[1]
        for step in job.steps_:
            if referenced_step_id == step.id_:
                yield from StepsIOMatch.__check_steps_ref_content(ref, step, job)
                return
        yield Problem(
            rule=StepsIOMatch.NAME,
            desc=(
                f"Step '{referenced_step_id.string}' in job '{job.job_id_}' does not exist"
            ),
            pos=ref.pos,
            level=ProblemLevel.ERR,
        )

    @staticmethod
    def __check_steps_ref_content(
        ref: ast.Expression,
        step: ast.Step,
        job: ast.Job,
    ) -> Generator[Problem, None, None]:
        if not isinstance(step.exec, ast.ExecAction):
            return  # TODO check for run exec type
        prev_step_metadata = parse_action(step.exec.uses_)

        ref_step_attr = ref.parts[2]  # e.g., outputs
        ref_step_var = ref.parts[3]
        if ref_step_attr in prev_step_metadata:
            type_: Dict[str, str] = prev_step_metadata[ref_step_attr]
            if type_ is None or len(type_) == 0:  # type is empty TODO check if none needed
                yield Problem(
                    rule=StepsIOMatch.NAME,
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
                    rule=StepsIOMatch.NAME,
                    desc=(
                        f"'{ref_step_var.string}' not as "
                        f"'{ref_step_attr.string}' in '{step.id_.string}'"
                    ),
                    level=ProblemLevel.ERR,
                    pos=ref.pos,
                )

        else:
            yield Problem(
                rule=StepsIOMatch.NAME,
                desc=f"'{ref_step_var.string}' does not exist in step",
                level=ProblemLevel.ERR,
                pos=ref.pos,
            )
