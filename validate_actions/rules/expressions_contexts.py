from collections.abc import Mapping, Sequence
from dataclasses import fields, is_dataclass
from typing import Generator, Optional

from validate_actions.problems import Problem, ProblemLevel
from validate_actions.rules.rule import Rule
from validate_actions.workflow.ast import Reference, Workflow
from validate_actions.workflow.contexts import Contexts


class ExpressionsContexts(Rule):
    NAME = 'expressions-contexts'

    @staticmethod
    def check(
        workflow: 'Workflow',
    ) -> Generator[Problem, None, None]:
        for ref in ExpressionsContexts._traverse(workflow):
            problem = ExpressionsContexts.does_expr_exist(ref, workflow.contexts)
            if problem:
                yield problem

    @staticmethod
    def _traverse(obj):
        if isinstance(obj, Reference):
            yield obj
        elif isinstance(obj, Contexts):
            return
        elif is_dataclass(obj):
            for f in fields(obj):
                try:
                    val = getattr(obj, f.name)
                except AttributeError:
                    continue
                yield from ExpressionsContexts._traverse(val)
        elif isinstance(obj, Mapping):
            for v in obj.values():
                yield from ExpressionsContexts._traverse(v)
        elif isinstance(obj, Sequence) and not isinstance(obj, (str, bytes)):
            for item in obj:
                yield from ExpressionsContexts._traverse(item)

    @staticmethod
    def does_expr_exist(
        expr: Reference,
        contexts: Contexts,
    ) -> Optional[Problem]:
        # Iteratively check each part of the expression against the context tree
        cur = contexts
        parts = expr.parts or []
        problem = Problem(
            pos=expr.pos,
            desc=f"Expression '{expr.string}' does not match any context",
            level=ProblemLevel.ERR,
            rule=ExpressionsContexts.NAME,
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
