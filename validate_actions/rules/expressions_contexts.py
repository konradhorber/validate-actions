from collections.abc import Mapping, Sequence
from dataclasses import fields, is_dataclass
from typing import Generator, Optional

from validate_actions.problems import Problem, ProblemLevel
from validate_actions.rules.rule import Rule
from validate_actions.workflow.ast import Expression, Workflow
from validate_actions.workflow.contexts import Contexts


class ExpressionsContexts(Rule):
    NAME = 'expressions-contexts'

    @staticmethod
    def check(
        workflow: 'Workflow',
    ) -> Generator[Problem, None, None]:
        # start traversal with the global workflow contexts
        for ref, ctx in ExpressionsContexts._traverse(workflow, workflow.contexts):
            problem = ExpressionsContexts.does_expr_exist(ref, ctx)
            if problem:
                yield problem

    @staticmethod
    def _traverse(obj, cur_context: Contexts):
        """
        Recursively traverse AST, yielding (Expression, Contexts) pairs.
        Update context when encountering a node with its own 'contexts' field.
        """
        # direct Expression: emit with current context
        if isinstance(obj, Expression):
            yield obj, cur_context
            return
        # skip walking inside the Contexts definitions themselves
        if isinstance(obj, Contexts):
            return
        # dataclass nodes: check for own contexts, then traverse fields
        if is_dataclass(obj):
            # switch to local context if available
            new_context = cur_context
            if hasattr(obj, 'contexts') and isinstance(getattr(obj, 'contexts'), Contexts):
                new_context = getattr(obj, 'contexts')
            for f in fields(obj):
                if f.name == 'contexts':
                    # do not traverse into context definitions
                    continue
                try:
                    val = getattr(obj, f.name)
                except AttributeError:
                    continue
                yield from ExpressionsContexts._traverse(val, new_context)
            return
        # mappings and sequences: propagate current context
        if isinstance(obj, Mapping):
            for v in obj.values():
                yield from ExpressionsContexts._traverse(v, cur_context)
            return
        if isinstance(obj, Sequence) and not isinstance(obj, (str, bytes)):
            for item in obj:
                yield from ExpressionsContexts._traverse(item, cur_context)
            return

    @staticmethod
    def does_expr_exist(
        expr: Expression,
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
            elif hasattr(cur, 'functions_') and part in getattr(cur, 'functions_'):
                cur = getattr(cur, 'functions_')[part]
            elif isinstance(cur, list) and part in cur:
                index = cur.index(part)
                cur = cur[index]

            else:
                return problem
        return None
