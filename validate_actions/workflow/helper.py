from typing import Any, Dict, List, Optional

from validate_actions.lint_problem import LintProblem
from validate_actions.workflow import ast


def build_env(
    env_vars: Dict[ast.String, Any],
    problems: List[LintProblem],
    RULE_NAME: str
) -> Optional[ast.Env]:
    env_vars_out: Dict[ast.String, ast.String] = {}
    for key in env_vars:
        if isinstance(key, ast.String) and isinstance(env_vars[key], ast.String):
            env_vars_out[key] = env_vars[key]
        else:
            problems.append(LintProblem(
                pos=key.pos,
                desc=f"Invalid environment variable value: {key.string}",
                level='error',
                rule=RULE_NAME
            ))
    if len(env_vars_out) == 0:
        problems.append(LintProblem(
            pos=ast.Pos(0, 0),
            desc="No valid environment variables found.",
            level='error',
            rule=RULE_NAME
        ))
        return None
    return ast.Env(env_vars_out)
