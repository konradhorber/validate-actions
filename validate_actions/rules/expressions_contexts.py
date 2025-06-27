from collections.abc import Mapping, Sequence
from dataclasses import fields, is_dataclass
from difflib import SequenceMatcher
from typing import Generator, Optional

from validate_actions.problems import Problem, ProblemLevel
from validate_actions.rules.rule import Rule
from validate_actions.workflow.ast import Expression, String
from validate_actions.workflow.contexts import Contexts


class ExpressionsContexts(Rule):
    NAME = "expressions-contexts"

    def check(
        self,
    ) -> Generator[Problem, None, None]:
        # start traversal with the global workflow contexts
        for ref, ctx in self._traverse(self.workflow, self.workflow.contexts):
            problem = self.does_expr_exist(ref, ctx)
            if problem:
                yield problem

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

        if any(op in expr.string for op in operators):  # TODO
            return None

        web_contexts_not_to_check = ["vars", "secrets", "inputs", "steps"]
        # TODO unshelf needs and steps
        if not parts:
            return problem
        parts_visited: list[String] = []
        for part in parts:
            if part in web_contexts_not_to_check:
                break
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
                # Get available options for error message
                available_options: list[str] = []
                if isinstance(cur, list):
                    available_options = cur
                else:
                    field_names = [f.name for f in fields(cur)]
                    available_options.extend(field_names)
                    if hasattr(cur, "children_"):
                        available_options.extend(cur.children_.keys())
                    elif hasattr(cur, "functions_"):
                        available_options.extend(cur.functions_.keys())

                # Find closest match for suggestion
                closest_match = None
                if available_options:
                    scores = {
                        opt: SequenceMatcher(None, part.string, opt).ratio()
                        for opt in available_options
                    }
                    best_match, best_score = max(scores.items(), key=lambda x: x[1])
                    if best_score > 0.6:  # Only suggest if reasonably similar
                        closest_match = best_match

                # Enhanced error message with context
                parts_visited_str = ".".join([p.string for p in parts_visited])
                context_path = (
                    f"in context '{parts_visited_str}'" if parts_visited_str else "at root level"
                )

                suggestion_text = ""
                if closest_match:
                    suggestion_text = f" Did you mean '{closest_match}'?"
                elif available_options:
                    options_list = "', '".join(
                        sorted(available_options)[:5]
                    )  # Show up to 5 options
                    more_text = (
                        f" (and {len(available_options) - 5} more)"
                        if len(available_options) > 5
                        else ""
                    )
                    suggestion_text = (
                        f" Available options {context_path}: '{options_list}'{more_text}"
                    )

                problem.desc = f"Expression '{expr.string}' does not match any context. Unknown property '{part.string}'{suggestion_text}"

                if self.fix:
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

                else:
                    return problem
            parts_visited.append(part)
        return None
