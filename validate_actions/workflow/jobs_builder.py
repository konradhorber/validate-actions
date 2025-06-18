import copy
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Set

from validate_actions.pos import Pos
from validate_actions.problems import Problem, ProblemLevel, Problems
from validate_actions.workflow import ast, helper
from validate_actions.workflow.contexts import (
    Contexts,
    ContextType,
    JobContext,
    JobsContext,
    JobVarContext,
    MatrixContext,
    RunnerContext,
    ServiceContext,
    StrategyContext,
)


class JobsBuilder(ABC):
    @abstractmethod
    def build(
        self,
        jobs_dict: Dict[ast.String, Any]
    ) -> Dict[ast.String, ast.Job]:
        """
        Build events from the input data.
        """
        pass


class BaseJobsBuilder(JobsBuilder):
    def __init__(
        self,
        problems: Problems,
        schema: Dict[str, Any],
        contexts: Contexts
    ) -> None:
        self.problems = problems
        self.RULE_NAME = 'jobs-syntax-error'
        self.schema = schema
        self.contexts = contexts

    def build(
        self,
        jobs_dict: Dict[ast.String, Any]
    ) -> Dict[ast.String, ast.Job]:
        jobs = {}
        jobs_context = JobsContext()
        for job_id, job_dict in jobs_dict.items():
            job_jobs_context = JobVarContext()
            jobs[job_id] = self.__build_job(job_dict, job_id, job_jobs_context)
            jobs_context.children_[job_id.string] = job_jobs_context
        self.contexts.jobs = jobs_context
        return jobs

    def __build_job(
        self,
        job_dict: Dict[ast.String, Any],
        job_id: ast.String,
        job_jobs_context: JobVarContext
    ) -> ast.Job:
        pos = Pos(
            line=job_id.pos.line,
            col=job_id.pos.col,
        )
        job_id_ = job_id.string
        name_: Optional[ast.String] = None
        permissions_: ast.Permissions = ast.Permissions()
        needs_ = None
        if_ = None
        runs_on_: Optional[ast.RunsOn] = None
        environment_ = None
        concurrency_ = None
        outputs_ = None
        env_: Optional[ast.Env] = None
        defaults_: Optional[ast.Defaults] = None
        steps_ = []
        timeout_minutes_: Optional[int] = None
        strategy_: Optional[ast.Strategy] = None
        container_ = None
        services_ = None
        uses_ = None
        with_ = None
        secrets_ = None
        job_context = JobContext()
        runner_context = RunnerContext()

        local_contexts = copy.copy(self.contexts)
        local_contexts.job = job_context
        local_contexts.runner = runner_context

        for key in job_dict:
            match key.string:
                case 'name':
                    name_ = job_dict[key]
                case 'permissions':
                    permissions_ = helper.build_permissions(
                        job_dict[key], self.problems, self.RULE_NAME
                    )
                case 'needs':
                    pass
                case 'if':
                    pass
                case 'runs-on':
                    runs_on_ = self._build_runs_on(
                        key, job_dict[key], self.problems, self.RULE_NAME
                    )
                case 'environment':
                    pass
                case 'concurrency':
                    pass
                case 'outputs':
                    self._build_jobs_context_output(key, job_dict, job_jobs_context)
                case 'env':
                    local_contexts.env = copy.deepcopy(local_contexts.env)
                    env_ = helper.build_env(
                        job_dict[key], local_contexts, self.problems, self.RULE_NAME
                    )
                case 'defaults':
                    defaults_ = helper.build_defaults(job_dict[key], self.problems, self.RULE_NAME)
                case 'steps':
                    steps_ = self.__build_steps(job_dict[key], local_contexts)
                case 'timeout-minutes':
                    timeout_minutes_ = job_dict[key]
                case 'strategy':
                    strategy_ = self._build_strategy(key, job_dict, local_contexts)
                case 'container':
                    pass
                case 'services':
                    self._build_job_context_services(job_dict[key], job_context)
                case 'uses':
                    pass
                case 'with':
                    pass
                case 'secrets':
                    pass
                case _:
                    self.problems.append(Problem(
                        pos=key.pos,
                        desc=f"Unknown job key: {key.string}",
                        level=ProblemLevel.ERR,
                        rule=self.RULE_NAME
                    ))

        return ast.Job(
            pos=pos,
            job_id_=job_id_,
            contexts=local_contexts,
            name_=name_,
            permissions_=permissions_,
            needs_=needs_,
            if_=if_,
            runs_on_=runs_on_,
            environment_=environment_,
            concurrency_=concurrency_,
            outputs_=outputs_,
            env_=env_,
            defaults_=defaults_,
            steps_=steps_,
            timeout_minutes_=timeout_minutes_,
            strategy_=strategy_,
            container_=container_,
            services_=services_,
            uses_=uses_,
            with_=with_,
            secrets_=secrets_
        )

    def _build_strategy(
        self,
        key: ast.String,
        job_dict: Dict[ast.String, Any],
        local_contexts: Contexts
    ) -> Optional[ast.Strategy]:
        strategy_data = job_dict[key]
        if not isinstance(strategy_data, dict):
            self.problems.append(Problem(
                pos=key.pos,
                desc="Strategy must be a mapping",
                level=ProblemLevel.ERR,
                rule=self.RULE_NAME
            ))
            return None

        combinations_ = None
        fail_fast_ = None
        max_parallel_ = None

        for strategy_key, strategy_value in strategy_data.items():
            if strategy_key.string == 'matrix':
                if not isinstance(strategy_value, dict):
                    self.problems.append(Problem(
                        pos=strategy_key.pos,
                        desc="Strategy matrix must be a mapping",
                        level=ProblemLevel.ERR,
                        rule=self.RULE_NAME
                    ))
                    continue
                combinations_ = self._build_matrix_combinations(
                    strategy_key, strategy_value, local_contexts
                    )
            elif strategy_key.string == 'fail-fast':
                if not isinstance(strategy_value, bool):
                    self.problems.append(Problem(
                        pos=strategy_key.pos,
                        desc="Strategy fail-fast must be a boolean",
                        level=ProblemLevel.ERR,
                        rule=self.RULE_NAME
                    ))
                    continue
                fail_fast_ = strategy_value
            elif strategy_key.string == 'max-parallel':
                if not isinstance(strategy_value, int):
                    self.problems.append(Problem(
                        pos=strategy_key.pos,
                        desc="Strategy max-parallel must be an integer",
                        level=ProblemLevel.ERR,
                        rule=self.RULE_NAME
                    ))
                    continue
                max_parallel_ = strategy_value
            else:
                self.problems.append(Problem(
                    pos=strategy_key.pos,
                    desc=f"Unknown strategy key: {strategy_key.string}",
                    level=ProblemLevel.ERR,
                    rule=self.RULE_NAME
                ))

        if combinations_ is None:
            # If matrix is not defined, but strategy key is present,
            # it could be just for fail-fast or max-parallel.
            # However, official docs imply matrix is usually there if strategy is used.
            # For now, let's allow strategy without matrix if other keys are present.
            # If only 'strategy:' is present with no sub-keys, it's an error.
            if not fail_fast_ and not max_parallel_ and not strategy_data.items():
                self.problems.append(Problem(
                    pos=key.pos,
                    desc="Strategy block is empty or invalid.",
                    level=ProblemLevel.ERR,
                    rule=self.RULE_NAME
                ))
                return None
            combinations_ = []  # Default to empty list if no matrix defined

        local_contexts.strategy = StrategyContext()
        return ast.Strategy(
            pos=key.pos,
            combinations=combinations_,
            fail_fast_=fail_fast_,
            max_parallel_=max_parallel_
        )

    def _parse_matrix_item_list(
        self,
        parent_key: ast.String,  # Key of 'include' or 'exclude'
        items_data: List[Any],
        item_type_str: str  # "include" or "exclude"
    ) -> List[Dict[ast.String, ast.String]]:
        parsed_items: List[Dict[ast.String, ast.String]] = []
        for item in items_data:
            if not isinstance(item, dict):
                self.problems.append(Problem(
                    pos=parent_key.pos,
                    desc=f"Each item in matrix {item_type_str} must be a mapping.",
                    level=ProblemLevel.ERR,
                    rule=self.RULE_NAME
                ))
                continue

            current_item_map: Dict[ast.String, ast.String] = {}
            valid_item = True
            for k, v in item.items():
                if not isinstance(k, ast.String):
                    self.problems.append(Problem(
                        pos=parent_key.pos,
                        desc=f"Key in matrix {item_type_str} item must be a string.",
                        level=ProblemLevel.ERR,
                        rule=self.RULE_NAME
                    ))
                    valid_item = False
                    break

                val_str: str
                val_pos: Pos
                if isinstance(v, ast.String):
                    val_str = v.string
                    val_pos = v.pos
                elif isinstance(v, (str, int, float, bool)):
                    val_str = str(v)
                    val_pos = k.pos  # Best guess for pos if not ast.String
                else:
                    self.problems.append(Problem(
                        pos=k.pos,
                        desc=(
                            f"Value for '{k.string}' in matrix {item_type_str} item must be a"
                            f" scalar (string, number, boolean)."
                        ),
                        level=ProblemLevel.ERR,
                        rule=self.RULE_NAME
                    ))
                    valid_item = False
                    break
                current_item_map[k] = ast.String(val_str, val_pos)

            if valid_item and current_item_map:
                parsed_items.append(current_item_map)
        return parsed_items

    def _build_matrix_combinations(
        self,
        matrix_key: ast.String,
        matrix_data: Dict[ast.String, Any],
        local_contexts: Contexts
    ) -> List[Dict[ast.String, ast.String]]:
        matrix_combinations: List[Dict[ast.String, ast.String]] = []
        include_items: List[Dict[ast.String, ast.String]] = []
        exclude_items: List[Dict[ast.String, ast.String]] = []
        matrix_axes: Dict[ast.String, List[Any]] = {}

        for key, value in matrix_data.items():
            if key.string == 'include':
                if not isinstance(value, list):
                    self.problems.append(Problem(
                        pos=key.pos,
                        desc="Matrix include must be a list of mappings",
                        level=ProblemLevel.ERR,
                        rule=self.RULE_NAME
                    ))
                    continue
                include_items = self._parse_matrix_item_list(key, value, "include")
            elif key.string == 'exclude':
                if not isinstance(value, list):
                    self.problems.append(Problem(
                        pos=key.pos,
                        desc="Matrix exclude must be a list of mappings",
                        level=ProblemLevel.ERR,
                        rule=self.RULE_NAME
                    ))
                    continue
                exclude_items = self._parse_matrix_item_list(key, value, "exclude")
            else:
                # This is a matrix axis
                if not isinstance(value, list):
                    self.problems.append(Problem(
                        pos=key.pos,
                        desc=f"Matrix axis '{key.string}' must be a list",
                        level=ProblemLevel.ERR,
                        rule=self.RULE_NAME
                    ))
                    continue
                matrix_axes[key] = value

        # Generate base matrix combinations from axes
        if matrix_axes:
            axis_names = list(matrix_axes.keys())
            import itertools

            # Ensure all values in axes are appropriate (e.g. ast.String or scalar)
            # For simplicity, we assume they are, or further validation is needed here
            raw_product = list(itertools.product(*[matrix_axes[k] for k in axis_names]))
            for combo_values in raw_product:
                current_combo: Dict[ast.String, ast.String] = {}
                valid_combo = True
                for i, axis_name_key in enumerate(axis_names):
                    val = combo_values[i]
                    val_str: str
                    val_pos: Pos
                    if isinstance(val, ast.String):
                        val_str = val.string
                        val_pos = val.pos
                    elif isinstance(val, (str, int, float, bool)):
                        val_str = str(val)
                        val_pos = axis_name_key.pos  # Best guess
                    else:
                        # This case should ideally be caught by earlier validation if axis values
                        # are restricted
                        self.problems.append(Problem(
                            pos=axis_name_key.pos,
                            desc=f"Unsupported value type in matrix axis '{axis_name_key.string}'",
                            level=ProblemLevel.ERR,
                            rule=self.RULE_NAME
                        ))
                        valid_combo = False
                        break
                    current_combo[axis_name_key] = ast.String(val_str, val_pos)
                if valid_combo:
                    matrix_combinations.append(current_combo)

        # Apply include
        if include_items:
            if not matrix_combinations:  # If only include is present
                matrix_combinations.extend(include_items)
            else:
                new_combinations_with_include = []
                for base_combo in matrix_combinations:
                    added_to_this_base = False
                    for include_item in include_items:
                        # Check if include_item can extend base_combo without overwrite
                        # or if include_item's matching keys match base_combo's values
                        merged_combo = base_combo.copy()
                        can_merge_or_match = True
                        temp_include_copy = include_item.copy()

                        for bk, bv in base_combo.items():
                            if bk in temp_include_copy:
                                if temp_include_copy[bk] != bv:  # Overwrite with different value
                                    can_merge_or_match = False
                                    break
                                del temp_include_copy[bk]  # Key matched, remove from temp_include

                        if can_merge_or_match:  # Add remaining new keys from include
                            merged_combo.update(temp_include_copy)
                            new_combinations_with_include.append(merged_combo)
                            added_to_this_base = True

                    if not added_to_this_base:  # If no include item specifically targeted this
                        new_combinations_with_include.append(base_combo)

                # Add include items that are entirely new (didn't merge with any base)
                for include_item in include_items:
                    is_completely_new = True
                    for combo in new_combinations_with_include:  # Check against already merged
                        # An include_item is new if it's not a subset of any existing combo
                        # AND no existing combo is a subset of it (unless it's an exact match)

                        # Simplified: if this include_item (or one that contains it) isn't already
                        is_present = True
                        for ik, iv in include_item.items():
                            if ik not in combo or combo[ik] != iv:
                                is_present = False
                                break
                        if is_present and len(include_item) <= len(combo):
                            is_completely_new = False
                            break
                    if is_completely_new:
                        new_combinations_with_include.append(include_item)
                matrix_combinations = new_combinations_with_include

        # Apply exclude
        if exclude_items:
            final_combinations = []
            for combo in matrix_combinations:
                is_excluded = False
                for exclude_item in exclude_items:
                    match = True  # Assume it matches until a mismatch is found
                    if not exclude_item:
                        continue  # Skip empty exclude item

                    for k_exc, v_exc in exclude_item.items():
                        if k_exc not in combo or combo[k_exc] != v_exc:
                            match = False
                            break
                    if match:  # If all keys in exclude_item match the combo
                        is_excluded = True
                        break
                if not is_excluded:
                    final_combinations.append(combo)
            matrix_combinations = final_combinations

        if not matrix_combinations and (matrix_axes or include_items):
            self.problems.append(Problem(
                pos=matrix_key.pos,
                desc="Matrix definition resulted in no job combinations after include/exclude.",
                level=ProblemLevel.WAR,
                rule=self.RULE_NAME
            ))

        # Update matrix context
        if local_contexts.matrix is None:
            local_contexts.matrix = MatrixContext()

        # Add all unique keys from all final combinations to the context
        all_matrix_keys: Set[str] = set()
        for combo in matrix_combinations:
            for k_combo in combo.keys():
                all_matrix_keys.add(k_combo.string)

        for key_str in all_matrix_keys:
            local_contexts.matrix.children_[key_str] = ContextType.string

        return matrix_combinations

    def __build_steps(
        self,
        steps_in: List[Dict[ast.String, Any]],
        job_local_context: Contexts
    ) -> List[ast.Step]:
        steps_out: List[ast.Step] = []
        for step in steps_in:
            steps_out.append(self.__build_step(step, job_local_context))
        return steps_out

    def __build_step(
        self,
        step_token_tree: Dict[ast.String, Any],
        job_local_context: Contexts
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

        local_context = job_local_context

        # build step inputs
        for key in step_token_tree:
            key_str = key.string
            match key_str:
                case 'id':
                    id_ = step_token_tree[key]
                case 'if':
                    if_ = step_token_tree[key]
                case 'name':
                    name_ = step_token_tree[key]
                case 'uses':
                    uses_ = step_token_tree[key]
                    exec_pos = Pos(
                        line=key.pos.line,
                        col=key.pos.col
                    )
                case 'run':
                    run_ = step_token_tree[key]
                    exec_pos = Pos(
                        line=key.pos.line,
                        col=key.pos.col
                    )
                case 'working-directory':
                    working_directory_ = step_token_tree[key]
                case 'shell':
                    shell_ = step_token_tree[key]
                case 'with':
                    for with_key, with_value in step_token_tree[key].items():
                        with_key_str = with_key.string

                        if with_key_str == 'args':
                            with_args_ = with_value
                        elif with_key_str == 'entrypoint':
                            with_entrypoint_ = with_value
                        else:
                            with_[with_key] = with_value
                case 'env':
                    local_context = copy.copy(local_context)
                    local_context.env = copy.deepcopy(local_context.env)
                    env_ = helper.build_env(
                        step_token_tree[key], local_context, self.problems, self.RULE_NAME
                    )
                case 'continue-on-error':
                    continue_on_error_ = step_token_tree[key]
                case 'timeout-minutes':
                    timeout_minutes_ = step_token_tree[key]
                case _:
                    self.problems.append(Problem(
                        pos=key.pos,
                        desc=f"Unknown step key: {key_str}",
                        level=ProblemLevel.ERR,
                        rule=self.RULE_NAME
                    ))

        exec: ast.Exec
        first_key_of_steps = next(iter(step_token_tree))
        pos = Pos(
            line=first_key_of_steps.pos.line,
            col=first_key_of_steps.pos.col
        )

        # create uses xor run exec for step
        if uses_ is None and run_ is None:
            self.problems.append(Problem(
                pos=pos,
                desc="Step must have either 'uses' or 'run' key",
                level=ProblemLevel.ERR,
                rule=self.RULE_NAME
            ))
        elif uses_ is not None and run_ is not None:
            self.problems.append(Problem(
                pos=pos,
                desc="Step cannot have both 'uses' and 'run' keys",
                level=ProblemLevel.ERR,
                rule=self.RULE_NAME
            ))
        elif uses_ is not None:
            exec = ast.ExecAction(
                pos=exec_pos,
                uses_=uses_,
                with_=with_,
                with_args_=with_args_,
                with_entrypoint_=with_entrypoint_
            )
        elif run_ is not None:
            exec = ast.ExecRun(
                pos=exec_pos,
                run_=run_,
                shell_=shell_,
                working_directory_=working_directory_
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
            timeout_minutes_=timeout_minutes_
        )

    def _build_jobs_context_output(
        self,
        key: ast.String,
        job_dict: Dict[ast.String, Any],
        job_jobs_context: JobVarContext
    ) -> None:
        """Generate output content for jobs context.

        Args:
            key (ast.String): The key where outputs are defined in the job.
            job_dict (Dict[ast.String, Any]): The dictionary representing the job.
            job_jobs_context (JobVarContext): The context for the job where outputs will be stored.
        """
        outputs = job_dict[key]

        # check that output is mapping, should always be
        if not isinstance(outputs, dict):
            self.problems.append(Problem(
                pos=key.pos,
                desc="Outputs must be a mapping",
                level=ProblemLevel.ERR,
                rule=self.RULE_NAME
            ))
            return

        outputs_context = job_jobs_context.outputs.children_

        for output_name in outputs:
            # check that output name is string, should always be
            if not isinstance(output_name, ast.String):
                self.problems.append(Problem(
                    pos=key.pos,
                    desc="Output name must be a string",
                    level=ProblemLevel.ERR,
                    rule=self.RULE_NAME
                ))
                continue

            # add output_name to job context
            outputs_context[output_name.string] = ContextType.string

    def _build_job_context_services(
        self,
        services_in: Dict[ast.String, Dict[ast.String, Any]],
        job_context: JobContext
    ) -> None:
        all_service_props = ['image', 'credentials', 'env', 'ports', 'volumes', 'options']
        for service_name, service_props in services_in.items():
            service_context = ServiceContext()

            for prop_name in service_props:
                if prop_name.string == 'ports':
                    port_mapping_list = service_props[prop_name]
                    for port_mapping in port_mapping_list:
                        port_str = port_mapping.string
                        sep = None
                        if ":" in port_str:
                            sep = ":"
                        elif "/" in port_str:
                            sep = "/"

                        left_part = port_str.split(sep)[0] if sep else port_str
                        service_context.ports.append(left_part)
                if prop_name.string not in all_service_props:
                    self.problems.append(Problem(
                        pos=service_name.pos,
                        desc=f"Unknown property '{prop_name.string}' in services",
                        level=ProblemLevel.ERR,
                        rule=self.RULE_NAME
                    ))

            job_context.services.children_[service_name.string] = service_context

    def _build_runs_on(
        self,
        key: ast.String,
        runs_on_value: Any,
        problems: Problems,
        rule_name: str
    ) -> Optional[ast.RunsOn]:
        """Builds the 'runs-on' value for a job."""
        cur_pos = Pos(line=key.pos.line, col=key.pos.col)
        problem = Problem(
            pos=cur_pos,
            desc="Invalid 'runs-on' value",
            level=ProblemLevel.ERR,
            rule=rule_name
        )
        labels: List[ast.String] = []
        group: List[ast.String] = []

        # helper to process 'labels' or 'group' items uniformly
        def handle_category(name: str, items: Any, pos: Pos) -> List[ast.String]:
            cat_problem = copy.copy(problem)
            cat_problem.pos = pos
            cat_problem.desc = f"Invalid syntax in 'runs-on' '{name}'"
            # single value
            if isinstance(items, ast.String):
                return [items]
            # list of values
            if isinstance(items, list):
                valid: List[ast.String] = []
                for itm in items:
                    if isinstance(itm, ast.String):
                        valid.append(itm)
                    else:
                        p = copy.copy(cat_problem)
                        p.desc = f"Invalid item in 'runs-on' '{name}': {itm}"
                        problems.append(p)
                return valid
            # invalid type
            p = copy.copy(cat_problem)
            p.desc = f"Invalid item in 'runs-on' '{name}': {items}"
            problems.append(p)
            return []

        # structured value handling
        if isinstance(runs_on_value, ast.String):
            labels.append(runs_on_value)
        elif isinstance(runs_on_value, list):
            for item in runs_on_value:
                if isinstance(item, ast.String):
                    labels.append(item)
                else:
                    problems.append(problem)
        elif isinstance(runs_on_value, dict):
            for category, items in runs_on_value.items():
                if not isinstance(category, ast.String):
                    problems.append(problem)
                    continue

                role = category.string
                if role == 'labels':
                    labels.extend(handle_category(role, items, category.pos))
                elif role == 'group':
                    group.extend(handle_category(role, items, category.pos))
                else:
                    unknown = copy.copy(problem)
                    unknown.pos = category.pos
                    unknown.desc = f"Unknown key in 'runs-on': {role}"
                    problems.append(unknown)
        else:
            problems.append(problem)
            return None

        return ast.RunsOn(
            pos=cur_pos,
            labels=labels,
            group=group
        )
