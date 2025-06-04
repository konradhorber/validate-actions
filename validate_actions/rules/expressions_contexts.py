from collections.abc import Mapping, Sequence
from dataclasses import fields, is_dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Generator, Optional

from validate_actions.problems import Problem, ProblemLevel
from validate_actions.rules.rule import Rule
from validate_actions.workflow.ast import Expression, String, Workflow
from validate_actions.workflow.contexts import Contexts


class ExpressionsContexts(Rule):
    NAME = 'expressions-contexts'

    @staticmethod
    def check(
        workflow: 'Workflow',
        fix: bool
    ) -> Generator[Problem, None, None]:
        # start traversal with the global workflow contexts
        for ref, ctx in ExpressionsContexts._traverse(workflow, workflow.contexts):
            problem = ExpressionsContexts.does_expr_exist(ref, ctx, fix, workflow)
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
        fix: bool,
        workflow: 'Workflow'
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
        operators = ['!', '<=', '<', '>=', '>', '==', '!=', '&&', '||']

        if any(op in expr.string for op in operators):  # TODO
            return None

        web_contexts_not_to_check = ['vars', 'secrets', 'inputs', 'needs', 'steps']
        # TODO unshelf needs and steps
        if not parts:
            return problem
        parts_visited = []
        for part in parts:
            if part in web_contexts_not_to_check:
                break
            if hasattr(cur, part.string):
                cur = getattr(cur, part.string)
            elif hasattr(cur, 'children_') and part.string in getattr(cur, 'children_'):
                cur = cur.children_[part.string]
            elif hasattr(cur, 'functions_') and part.string in getattr(cur, 'functions_'):
                cur = getattr(cur, 'functions_')[part.string]
            elif isinstance(cur, list) and part.string in cur:
                index = cur.index(part.string)
                cur = cur[index]
            else:
                if fix:
                    field_names = []
                    others: list[str] = []
                    others_scores = {}
                    fields_scores = {}
                    if isinstance(cur, list):
                        others = cur
                    else:
                        field_names = [f.name for f in fields(cur)]
                        if hasattr(cur, 'children_'):
                            others = cur.children_.keys()
                        elif hasattr(cur, 'functions_'):
                            others = list(cur.functions_.keys())

                        for key in field_names:
                            score = SequenceMatcher(None, part.string, key).ratio()
                            fields_scores[key] = score

                    for key in others:
                        score = SequenceMatcher(None, part.string, key).ratio()
                        others_scores[key] = score

                    fields_best_match = max(
                        fields_scores.items(), key=lambda x: x[1], default=(None, 0)
                        )
                    others_best_match = max(
                        others_scores.items(), key=lambda x: x[1], default=(None, 0)
                    )
                    fields_best_key, fields_best_score = fields_best_match
                    others_best_key, others_best_score = others_best_match

                    threshold = 0.8
                    max_key: str = ""
                    if fields_best_score > threshold and others_best_score > threshold:
                        candidates = [
                            k for k in [fields_best_key, others_best_key] if k is not None
                        ]
                        if candidates:
                            max_key = max(candidates, key=lambda x: len(x))
                        else:
                            max_key = ""
                    elif fields_best_score > threshold:
                        max_key = fields_best_key or ""
                    elif others_best_score > threshold:
                        max_key = others_best_key or ""
                    else:
                        return problem

                    return ExpressionsContexts.edit_yaml_at_position(
                        expression=expr,
                        part=part,
                        file_path=workflow.path,
                        idx=part.pos.idx,
                        num_delete=len(part.string),
                        new_text=max_key,
                        problem=problem,
                    )

                else:
                    return problem
            parts_visited.append(part)
        return None

    @staticmethod
    def edit_yaml_at_position(
        expression: Expression,
        part: String,
        file_path: Path,
        idx: int,
        num_delete: int,
        new_text: str,
        problem: Problem
    ) -> Optional[Problem]:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            if idx < 0 or idx >= len(content):
                return problem

            # Perform edit: delete and insert
            updated_content = (
                content[:idx] +
                new_text +
                content[idx + num_delete:]
            )

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(updated_content)

            problem.desc = (
                f"Fixed '${{{{ {expression.string} }}}}': changed '{part.string}' to '{new_text}'"
            )
            problem.level = ProblemLevel.NON

        except (OSError, ValueError, TypeError, UnicodeError):
            return problem
        finally:
            return problem
