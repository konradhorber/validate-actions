"""Validates expressions against workflow contexts."""
import re
from collections.abc import Mapping, Sequence
from dataclasses import fields, is_dataclass
from difflib import SequenceMatcher
from typing import Generator, Optional

from validate_actions.domain_model.contexts import Contexts
from validate_actions.domain_model.primitives import Expression, String
from validate_actions.globals.problems import Problem, ProblemLevel
from validate_actions.rules.rule import Rule


class ExpressionsContexts(Rule):
    NAME = "expressions-contexts"

    # ====================
    # MAIN VALIDATION METHODS
    # ====================

    def check(
        self,
    ) -> Generator[Problem, None, None]:
        # start traversal with the global workflow contexts
        for ref, ctx in self._traverse(self.workflow, self.workflow.contexts):
            problem = self.does_expr_exist(ref, ctx)
            if problem:
                yield problem

    def does_expr_exist(self, expr: Expression, contexts: Contexts) -> Optional[Problem]:
        # Iteratively check each part of the expression against the context tree
        cur = contexts
        parts = expr.parts or []
        problem = Problem(
            pos=expr.pos,
            desc=f"Expression '{expr.string}' does not match any context",
            level=ProblemLevel.ERR,
            rule=self.NAME,
        )
        operators = ["!", "<=", "<", ">=", ">", "==", "!=", "&&", "||"]
        function_regex = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(\s*([^)]*?)\s*\)")

        if any(op in expr.string for op in operators):  # TODO
            return None

        if function_regex.search(expr.string):
            return None

        web_contexts_not_to_check = ["vars", "secrets", "inputs", "steps", "env"]
        # TODO unshelf needs and steps
        if not parts:
            return problem
        # If one part it is a literal
        if len(parts) == 1:
            return None
        parts_visited: list[String] = []
        if parts[0] in web_contexts_not_to_check:
            return None
        if parts[0] == "github" and parts[1] == "event":
            return None
        for i, part in enumerate(parts):
            if hasattr(cur, part.string):
                cur = getattr(cur, part.string)
            elif hasattr(cur, "children_") and part.string in getattr(cur, "children_"):
                cur = cur.children_[part.string]
            elif hasattr(cur, "functions_") and part.string in getattr(cur, "functions_"):
                cur = getattr(cur, "functions_")[part.string]
            elif isinstance(cur, list) and part.string in cur:
                index = cur.index(part.string)
                cur = cur[index]
            else:
                problem.desc = (
                    f"Expression '{expr.string}' does not match any context. "
                    f"Unknown property '{part.string}'"
                )

                return self._fix_unknown_property(expr, part, cur, problem)
            parts_visited.append(part)
        return None

    # ====================
    # UTILITY METHODS
    # ====================

    def _traverse(self, obj, cur_context: Contexts):
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
            if hasattr(obj, "contexts") and isinstance(getattr(obj, "contexts"), Contexts):
                new_context = getattr(obj, "contexts")
            for f in fields(obj):
                if f.name == "contexts":
                    # do not traverse into context definitions
                    continue
                try:
                    val = getattr(obj, f.name)
                except AttributeError:
                    continue
                yield from self._traverse(val, new_context)
            return
        # mappings and sequences: propagate current context
        if isinstance(obj, Mapping):
            for v in obj.values():
                yield from self._traverse(v, cur_context)
            return
        if isinstance(obj, Sequence) and not isinstance(obj, (str, bytes)):
            for item in obj:
                yield from self._traverse(item, cur_context)
            return

    # ====================
    # FIXING METHODS
    # ====================

    def _fix_unknown_property(
        self, expr: Expression, part: String, cur, problem: Problem
    ) -> Problem:
        """Fix unknown property by finding and suggesting the best match."""
        field_names = []
        others: list[str] = []
        others_scores = {}
        fields_scores = {}
        if isinstance(cur, list):
            others = cur
        else:
            field_names = [f.name for f in fields(cur)]
            if hasattr(cur, "children_"):
                others = cur.children_.keys()
            elif hasattr(cur, "functions_"):
                others = list(cur.functions_.keys())

            for key in field_names:
                score = SequenceMatcher(None, part.string, key).ratio()
                fields_scores[key] = score

        for key in others:
            score = SequenceMatcher(None, part.string, key).ratio()
            others_scores[key] = score

        fields_best_match = max(fields_scores.items(), key=lambda x: x[1], default=(None, 0))
        others_best_match = max(others_scores.items(), key=lambda x: x[1], default=(None, 0))
        fields_best_key, fields_best_score = fields_best_match
        others_best_key, others_best_score = others_best_match

        threshold = 0.8
        max_key: str = ""
        if fields_best_score > threshold and others_best_score > threshold:
            candidates = [k for k in [fields_best_key, others_best_key] if k is not None]
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

        updated_problem_desc = (
            f"Fixed '${{{{ {expr.string} }}}}': changed '{part.string}' to '{max_key}'"
        )

        return self.fixer.edit_yaml_at_position(
            idx=part.pos.idx,
            old_text=part.string,
            new_text=max_key,
            problem=problem,
            new_problem_desc=updated_problem_desc,
        )
