from typing import Optional

from validate_actions.pos import Pos
from validate_actions.problems import Problem, ProblemLevel
from validate_actions.workflow.ast import Reference
from validate_actions.workflow.contexts import Contexts


def does_expr_exist(
    expr: Reference,
    contexts: Contexts,
) -> Optional[Problem]:
    # Iteratively check each part of the expression against the context tree
    cur = contexts
    parts = expr.parts or []
    problem = Problem(
        pos=Pos(line=0, col=0),
        desc=f"Expression '{expr.string}' does not match any context",
        level=ProblemLevel.ERR,
        rule='expression'
    )
    if not parts:
        return problem
    for part in parts:
        if hasattr(cur, part):
            cur = getattr(cur, part)
        elif hasattr(cur, 'children_') and part in getattr(cur, 'children_'):
            cur = cur.children_[part]
        else:
            return problem
    return None
