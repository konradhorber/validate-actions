"""Default implementation of a builder for steps."""
import copy
from typing import Any, Dict, List, Optional

from validate_actions.domain_model import ast
from validate_actions.domain_model.contexts import Contexts
from validate_actions.domain_model.primitives import Pos
from validate_actions.globals.problems import Problem, ProblemLevel, Problems
from validate_actions.pipeline_stages.builders.interfaces import (
    SharedComponentsBuilder,
    StepsBuilder,
)


class DefaultStepsBuilder(StepsBuilder):
    """Default implementation of a builder for steps."""
    def __init__(
        self,
        problems: Problems,
        contexts: Contexts,
        shared_components_builder: SharedComponentsBuilder,
    ) -> None:
        self.problems = problems
        self.RULE_NAME = "steps-syntax-error"
        self.contexts = contexts
        self.shared_components_builder = shared_components_builder

    def build(
        self,
        steps_in: List[Dict[ast.String, Any]],
        local_contexts: Contexts,
        container: Optional[ast.Container] = None,
    ) -> List[ast.Step]:
        steps_out: List[ast.Step] = []
        for step in steps_in:
            steps_out.append(self.__build_step(step, local_contexts, container))
        return steps_out

    def __build_step(
        self,
        step_token_tree: Dict[ast.String, Any],
        local_contexts: Contexts,
        container: Optional[ast.Container],
    ) -> ast.Step:
        pos: Pos
        id_ = None
        if_ = None
        name_ = None
        uses_ = None
        run_ = None
        working_directory_ = None
        shell_ = None
        with_ = {}
        with_args_ = None
        with_entrypoint_ = None
        env_: Optional[ast.Env] = None
        continue_on_error_ = None
        timeout_minutes_ = None

        exec_pos: Pos

        local_context = copy.copy(local_contexts)

        # build step inputs
        for key in step_token_tree:
            key_str = key.string
            match key_str:
                case "id":
                    id_ = step_token_tree[key]
                case "if":
                    if_ = step_token_tree[key]
                case "name":
                    name_ = step_token_tree[key]
                case "uses":
                    uses_ = step_token_tree[key]
                    exec_pos = Pos(line=key.pos.line, col=key.pos.col)
                case "run":
                    run_ = step_token_tree[key]
                    exec_pos = Pos(line=key.pos.line, col=key.pos.col)
                case "working-directory":
                    working_directory_ = step_token_tree[key]
                case "shell":
                    shell_ = step_token_tree[key]
                case "with":
                    for with_key, with_value in step_token_tree[key].items():
                        with_key_str = with_key.string

                        if container is not None and with_key_str in ("args", "entrypoint"):
                            if with_key_str == "args":
                                with_args_ = with_value
                            else:  # must be "entrypoint"
                                with_entrypoint_ = with_value
                        else:
                            with_[with_key] = with_value
                case "env":
                    env_ = self.shared_components_builder.build_env(step_token_tree[key])
                case "continue-on-error":
                    continue_on_error_ = step_token_tree[key]
                case "timeout-minutes":
                    timeout_minutes_ = step_token_tree[key]
                case _:
                    self.problems.append(
                        Problem(
                            pos=key.pos,
                            desc=f"Unknown step key: {key_str}",
                            level=ProblemLevel.ERR,
                            rule=self.RULE_NAME,
                        )
                    )

        exec: ast.Exec
        first_key_of_steps = next(iter(step_token_tree))
        pos = Pos(line=first_key_of_steps.pos.line, col=first_key_of_steps.pos.col)

        # create uses xor run exec for step
        if uses_ is None and run_ is None:
            self.problems.append(
                Problem(
                    pos=pos,
                    desc="Step must have either 'uses' or 'run' key",
                    level=ProblemLevel.ERR,
                    rule=self.RULE_NAME,
                )
            )
        elif uses_ is not None and run_ is not None:
            self.problems.append(
                Problem(
                    pos=pos,
                    desc="Step cannot have both 'uses' and 'run' keys",
                    level=ProblemLevel.ERR,
                    rule=self.RULE_NAME,
                )
            )
        elif uses_ is not None:
            exec = ast.ExecAction(
                pos=exec_pos,
                uses_=uses_,
                with_=with_,
                with_args_=with_args_,
                with_entrypoint_=with_entrypoint_,
            )
        elif run_ is not None:
            exec = ast.ExecRun(
                pos=exec_pos,
                run_=run_,
                shell_=shell_,
                working_directory_=working_directory_,
            )

        # create step
        return ast.Step(
            pos=pos,
            contexts=local_context,
            id_=id_,
            if_=if_,
            name_=name_,
            exec=exec,
            env_=env_,
            continue_on_error_=continue_on_error_,
            timeout_minutes_=timeout_minutes_,
        )
