"""Default implementation of a builder for jobs."""
import copy
import itertools
from typing import Any, Dict, List, Optional, Set

from validate_actions.domain_model import ast, contexts
from validate_actions.domain_model.contexts import (
    Contexts,
    ContextType,
    JobContext,
    JobsContext,
    JobVarContext,
    MatrixContext,
    RunnerContext,
    StrategyContext,
)
from validate_actions.domain_model.primitives import Pos
from validate_actions.globals.problems import Problem, ProblemLevel, Problems
from validate_actions.pipeline_stages.builders.interfaces import (
    JobsBuilder,
    SharedComponentsBuilder,
)
from validate_actions.pipeline_stages.builders.steps_builder import (
    DefaultStepsBuilder as StepsBuilder,
)


class DefaultJobsBuilder(JobsBuilder):
    """Default implementation of a builder for jobs"""
    def __init__(
        self,
        problems: Problems,
        steps_builder: StepsBuilder,
        contexts: Contexts,
        shared_components_builder: SharedComponentsBuilder,
    ) -> None:
        self.problems = problems
        self.RULE_NAME = "jobs-syntax-error"
        self.contexts = contexts
        self.steps_builder = steps_builder
        self.shared_components_builder = shared_components_builder

    def build(self, jobs_dict: Dict[ast.String, Any]) -> Dict[ast.String, ast.Job]:
        jobs = {}
        jobs_context = JobsContext()
        for job_id, job_dict in jobs_dict.items():
            job_jobs_context = JobVarContext()
            jobs[job_id] = self.__build_job(job_dict, job_id, job_jobs_context)
            jobs_context.children_[job_id.string] = job_jobs_context
        self.contexts.jobs = jobs_context
        return jobs

    def __build_job(
        self, job_dict: Dict[ast.String, Any], job_id: ast.String, job_jobs_context: JobVarContext
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
        environment_: Optional[ast.Environment] = None
        concurrency_: Optional[ast.Concurrency] = None
        outputs_ = None
        env_: Optional[ast.Env] = None
        defaults_: Optional[ast.Defaults] = None
        steps_ = []
        timeout_minutes_: Optional[int] = None
        strategy_: Optional[ast.Strategy] = None
        container_ = None
        services_ = None
        uses_ = None
        with_ = {}
        secrets_ = None
        job_context = JobContext()
        runner_context = RunnerContext()

        local_contexts = copy.copy(self.contexts)
        local_contexts.jobs = None
        local_contexts.job = job_context
        local_contexts.runner = runner_context

        for key in job_dict:
            match key.string:
                case "name":
                    name_ = job_dict[key]
                case "permissions":
                    permissions_ = self.shared_components_builder.build_permissions(job_dict[key])
                case "needs":
                    needs_ = self._build_needs(key, job_dict[key])
                case "if":
                    if_ = self._build_if(key, job_dict[key])
                case "runs-on":
                    runs_on_ = self._build_runs_on(
                        key, job_dict[key], self.problems, self.RULE_NAME
                    )
                case "environment":
                    environment_ = self._build_environment(
                        key, job_dict[key], self.problems, self.RULE_NAME
                    )
                case "concurrency":
                    concurrency_ = self.shared_components_builder.build_concurrency(
                        key, job_dict[key]
                    )
                case "outputs":
                    self._build_jobs_context_output(key, job_dict, job_jobs_context)
                case "env":
                    env_ = self.shared_components_builder.build_env(job_dict[key])
                case "defaults":
                    defaults_ = self.shared_components_builder.build_defaults(job_dict[key])
                case "steps":
                    steps_ = self.steps_builder.build(job_dict[key], local_contexts, container_)
                case "timeout-minutes":
                    timeout_minutes_ = job_dict[key]
                case "strategy":
                    strategy_ = self._build_strategy(key, job_dict, local_contexts)
                case "container":
                    container_ = self._build_container(
                        key, job_dict[key], local_contexts, self.problems, self.RULE_NAME
                    )
                case "services":
                    self._build_job_context_services(job_dict[key], job_context)
                case "uses":
                    value = job_dict[key]
                    if isinstance(value, ast.String):
                        uses_ = value
                    else:
                        self.problems.append(
                            Problem(
                                pos=key.pos,
                                desc="Invalid 'uses' value, it must be a string.",
                                level=ProblemLevel.ERR,
                                rule=self.RULE_NAME,
                            )
                        )
                case "with":
                    value = job_dict[key]
                    if isinstance(value, dict):
                        for with_key, with_value in value.items():
                            with_[with_key] = with_value
                    else:
                        self.problems.append(
                            Problem(
                                pos=key.pos,
                                desc="Invalid 'with' value: must be a mapping.",
                                level=ProblemLevel.ERR,
                                rule=self.RULE_NAME,
                            )
                        )
                case "secrets":
                    secrets_ = self._build_secrets(
                        key, job_dict[key], self.problems, self.RULE_NAME
                    )
                case _:
                    self.problems.append(
                        Problem(
                            pos=key.pos,
                            desc=f"Unknown job key: {key.string}",
                            level=ProblemLevel.ERR,
                            rule=self.RULE_NAME,
                        )
                    )

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
            secrets_=secrets_,
        )

    def _build_container(
        self,
        container_key: ast.String,
        container_data: Any,
        local_contexts: Contexts,
        problems: Problems,
        rule_name: str,
    ) -> Optional[ast.Container]:
        if isinstance(container_data, ast.String):
            return ast.Container(pos=container_data.pos, image_=container_data)

        if not isinstance(container_data, dict):
            problems.append(
                Problem(
                    pos=container_key.pos,
                    desc="Container must be a string or a mapping.",
                    level=ProblemLevel.ERR,
                    rule=rule_name,
                )
            )
            return None

        image_ = None
        credentials_ = None
        env_ = None
        ports_ = None
        volumes_ = None
        options_ = None

        for key, value in container_data.items():
            match key.string:
                case "image":
                    if isinstance(value, ast.String):
                        image_ = value
                    else:
                        problems.append(
                            Problem(
                                pos=key.pos,
                                desc="Container image must be a string.",
                                level=ProblemLevel.ERR,
                                rule=rule_name,
                            )
                        )
                case "credentials":
                    credentials_ = self._build_container_credentials(
                        key, value, problems, rule_name
                    )
                case "env":
                    env_ = self.shared_components_builder.build_env(value)
                case "ports":
                    if isinstance(value, list) and all(isinstance(i, ast.String) for i in value):
                        ports_ = value
                    else:
                        problems.append(
                            Problem(
                                pos=key.pos,
                                desc="Container ports must be a list of strings.",
                                level=ProblemLevel.ERR,
                                rule=rule_name,
                            )
                        )
                case "volumes":
                    if isinstance(value, list) and all(isinstance(i, ast.String) for i in value):
                        volumes_ = value
                    else:
                        problems.append(
                            Problem(
                                pos=key.pos,
                                desc="Container volumes must be a list of strings.",
                                level=ProblemLevel.ERR,
                                rule=rule_name,
                            )
                        )
                case "options":
                    if isinstance(value, ast.String):
                        options_ = value
                    else:
                        problems.append(
                            Problem(
                                pos=key.pos,
                                desc="Container options must be a string.",
                                level=ProblemLevel.ERR,
                                rule=rule_name,
                            )
                        )
                case _:
                    problems.append(
                        Problem(
                            pos=key.pos,
                            desc=f"Unknown container key: {key.string}",
                            level=ProblemLevel.ERR,
                            rule=rule_name,
                        )
                    )

        if image_ is None:
            problems.append(
                Problem(
                    pos=container_key.pos,
                    desc="Container must have an 'image' property.",
                    level=ProblemLevel.ERR,
                    rule=rule_name,
                )
            )
            return None

        return ast.Container(
            pos=container_key.pos,
            image_=image_,
            credentials_=credentials_,
            env_=env_,
            ports_=ports_,
            volumes_=volumes_,
            options_=options_,
        )

    def _build_container_credentials(
        self,
        credentials_key: ast.String,
        credentials_data: Any,
        problems: Problems,
        rule_name: str,
    ) -> Optional[ast.ContainerCredentials]:
        if not isinstance(credentials_data, dict):
            problems.append(
                Problem(
                    pos=credentials_key.pos,
                    desc="Container credentials must be a mapping.",
                    level=ProblemLevel.ERR,
                    rule=rule_name,
                )
            )
            return None

        username_ = None
        password_ = None

        for key, value in credentials_data.items():
            match key.string:
                case "username":
                    if isinstance(value, ast.String):
                        username_ = value
                    else:
                        problems.append(
                            Problem(
                                pos=key.pos,
                                desc="Credentials username must be a string.",
                                level=ProblemLevel.ERR,
                                rule=rule_name,
                            )
                        )
                case "password":
                    if isinstance(value, ast.String):
                        password_ = value
                    else:
                        problems.append(
                            Problem(
                                pos=key.pos,
                                desc="Credentials password must be a string.",
                                level=ProblemLevel.ERR,
                                rule=rule_name,
                            )
                        )
                case _:
                    problems.append(
                        Problem(
                            pos=key.pos,
                            desc=f"Unknown credentials key: {key.string}",
                            level=ProblemLevel.ERR,
                            rule=rule_name,
                        )
                    )

        if username_ is None or password_ is None:
            problems.append(
                Problem(
                    pos=credentials_key.pos,
                    desc="Container credentials must have 'username' and 'password'.",
                    level=ProblemLevel.ERR,
                    rule=rule_name,
                )
            )
            return None

        return ast.ContainerCredentials(
            pos=credentials_key.pos, username_=username_, password_=password_
        )

    def _build_secrets(
        self, secrets_key: ast.String, secrets_data: Any, problems: Problems, rule_name: str
    ) -> Optional[ast.Secrets]:
        if isinstance(secrets_data, ast.String) and secrets_data.string == "inherit":
            return ast.Secrets(pos=secrets_key.pos, inherit=True)

        if isinstance(secrets_data, dict):
            secrets_map = {}
            for key, value in secrets_data.items():
                if isinstance(value, ast.String):
                    secrets_map[key] = value
                else:
                    problems.append(
                        Problem(
                            pos=key.pos,
                            desc="Each secret value must be a string.",
                            level=ProblemLevel.ERR,
                            rule=rule_name,
                        )
                    )
            return ast.Secrets(pos=secrets_key.pos, secrets=secrets_map)

        problems.append(
            Problem(
                pos=secrets_key.pos,
                desc="Invalid 'secrets' value: must be a mapping or 'inherit'.",
                level=ProblemLevel.ERR,
                rule=rule_name,
            )
        )
        return None

    def _build_strategy(
        self, key: ast.String, job_dict: Dict[ast.String, Any], local_contexts: Contexts
    ) -> Optional[ast.Strategy]:
        strategy_data = job_dict[key]
        if not isinstance(strategy_data, dict):
            self.problems.append(
                Problem(
                    pos=key.pos,
                    desc="Strategy must be a mapping",
                    level=ProblemLevel.ERR,
                    rule=self.RULE_NAME,
                )
            )
            return None

        combinations_ = None
        fail_fast_ = None
        max_parallel_ = None

        for strategy_key, strategy_value in strategy_data.items():
            if strategy_key == "matrix":
                if isinstance(strategy_value, ast.String):
                    if strategy_value == "$codeql-languages-matrix":
                        strategy_value = {
                            ast.String("language", strategy_value.pos): ast.String(
                                "selected by codeql", strategy_value.pos
                            ),
                            ast.String("build-mode", strategy_value.pos): ast.String(
                                "selected by codeql", strategy_value.pos
                            ),
                        }
                    else:
                        self.problems.append(
                            Problem(
                                pos=strategy_key.pos,
                                desc="Matrix must be a mapping",
                                level=ProblemLevel.ERR,
                                rule=self.RULE_NAME,
                            )
                        )
                        continue
                if not isinstance(strategy_value, dict):
                    self.problems.append(
                        Problem(
                            pos=strategy_key.pos,
                            desc="Strategy matrix must be a mapping",
                            level=ProblemLevel.ERR,
                            rule=self.RULE_NAME,
                        )
                    )
                    continue
                combinations_ = self._build_matrix_combinations(
                    strategy_key, strategy_value, local_contexts
                )
            elif strategy_key.string == "fail-fast":
                if not isinstance(strategy_value, bool):
                    self.problems.append(
                        Problem(
                            pos=strategy_key.pos,
                            desc="Strategy fail-fast must be a boolean",
                            level=ProblemLevel.ERR,
                            rule=self.RULE_NAME,
                        )
                    )
                    continue
                fail_fast_ = strategy_value
            elif strategy_key.string == "max-parallel":
                if not isinstance(strategy_value, int):
                    self.problems.append(
                        Problem(
                            pos=strategy_key.pos,
                            desc="Strategy max-parallel must be an integer",
                            level=ProblemLevel.ERR,
                            rule=self.RULE_NAME,
                        )
                    )
                    continue
                max_parallel_ = strategy_value
            else:
                self.problems.append(
                    Problem(
                        pos=strategy_key.pos,
                        desc=f"Unknown strategy key: {strategy_key.string}",
                        level=ProblemLevel.ERR,
                        rule=self.RULE_NAME,
                    )
                )

        if combinations_ is None:
            # If matrix is not defined, but strategy key is present,
            # it could be just for fail-fast or max-parallel.
            # However, official docs imply matrix is usually there if strategy is used.
            # For now, let's allow strategy without matrix if other keys are present.
            # If only 'strategy:' is present with no sub-keys, it's an error.
            if not fail_fast_ and not max_parallel_ and not strategy_data.items():
                self.problems.append(
                    Problem(
                        pos=key.pos,
                        desc="Strategy block is empty or invalid.",
                        level=ProblemLevel.ERR,
                        rule=self.RULE_NAME,
                    )
                )
                return None
            combinations_ = []  # Default to empty list if no matrix defined

        local_contexts.strategy = StrategyContext()
        return ast.Strategy(
            pos=key.pos,
            combinations=combinations_,
            fail_fast_=fail_fast_,
            max_parallel_=max_parallel_,
        )

    def _parse_matrix_item_list(
        self,
        parent_key: ast.String,  # Key of 'include' or 'exclude'
        items_data: List[Any],
        item_type_str: str,  # "include" or "exclude"
    ) -> List[Dict[ast.String, ast.String]]:
        parsed_items: List[Dict[ast.String, ast.String]] = []
        for item in items_data:
            if not isinstance(item, dict):
                self.problems.append(
                    Problem(
                        pos=parent_key.pos,
                        desc=f"Each item in matrix {item_type_str} must be a mapping.",
                        level=ProblemLevel.ERR,
                        rule=self.RULE_NAME,
                    )
                )
                continue

            current_item_map: Dict[ast.String, ast.String] = {}
            valid_item = True
            for k, v in item.items():
                if not isinstance(k, ast.String):
                    self.problems.append(
                        Problem(
                            pos=parent_key.pos,
                            desc=f"Key in matrix {item_type_str} item must be a string.",
                            level=ProblemLevel.ERR,
                            rule=self.RULE_NAME,
                        )
                    )
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
                    self.problems.append(
                        Problem(
                            pos=k.pos,
                            desc=(
                                f"Value for '{k.string}' in matrix {item_type_str} item must be a"
                                f" scalar (string, number, boolean)."
                            ),
                            level=ProblemLevel.ERR,
                            rule=self.RULE_NAME,
                        )
                    )
                    valid_item = False
                    break
                current_item_map[k] = ast.String(val_str, val_pos)

            if valid_item and current_item_map:
                parsed_items.append(current_item_map)
        return parsed_items

    def _build_matrix_combinations(
        self, matrix_key: ast.String, matrix_data: Dict[ast.String, Any], local_contexts: Contexts
    ) -> List[Dict[ast.String, ast.String]]:
        matrix_combinations: List[Dict[ast.String, ast.String]] = []
        include_items: List[Dict[ast.String, ast.String]] = []
        exclude_items: List[Dict[ast.String, ast.String]] = []
        matrix_axes: Dict[ast.String, List[Any]] = {}

        for key, value in matrix_data.items():
            if key.string == "include":
                if not isinstance(value, list):
                    self.problems.append(
                        Problem(
                            pos=key.pos,
                            desc="Matrix include must be a list of mappings",
                            level=ProblemLevel.ERR,
                            rule=self.RULE_NAME,
                        )
                    )
                    continue
                include_items = self._parse_matrix_item_list(key, value, "include")
            elif key.string == "exclude":
                if not isinstance(value, list):
                    self.problems.append(
                        Problem(
                            pos=key.pos,
                            desc="Matrix exclude must be a list of mappings",
                            level=ProblemLevel.ERR,
                            rule=self.RULE_NAME,
                        )
                    )
                    continue
                exclude_items = self._parse_matrix_item_list(key, value, "exclude")
            else:
                # This is a matrix axis
                if not isinstance(value, list):
                    if not isinstance(value, (ast.String, str, int, float, bool)):
                        self.problems.append(
                            Problem(
                                pos=key.pos,
                                desc=(f"Matrix axis '{key.string}' value invalid"),
                                level=ProblemLevel.ERR,
                                rule=self.RULE_NAME,
                            )
                        )
                        continue
                    value = [value]
                matrix_axes[key] = value

        # Generate base matrix combinations from axes
        if matrix_axes:
            axis_names = list(matrix_axes.keys())

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
                        self.problems.append(
                            Problem(
                                pos=axis_name_key.pos,
                                desc=(
                                    f"Unsupported value type in matrix axis "
                                    f"'{axis_name_key.string}'"
                                ),
                                level=ProblemLevel.ERR,
                                rule=self.RULE_NAME,
                            )
                        )
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
            self.problems.append(
                Problem(
                    pos=matrix_key.pos,
                    desc=(
                        "Matrix definition resulted in no job combinations "
                        "after include/exclude."
                    ),
                    level=ProblemLevel.WAR,
                    rule=self.RULE_NAME,
                )
            )

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

    def _build_jobs_context_output(
        self, key: ast.String, job_dict: Dict[ast.String, Any], job_jobs_context: JobVarContext
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
            self.problems.append(
                Problem(
                    pos=key.pos,
                    desc="Outputs must be a mapping",
                    level=ProblemLevel.ERR,
                    rule=self.RULE_NAME,
                )
            )
            return

        outputs_context = job_jobs_context.outputs.children_

        for output_name in outputs:
            # check that output name is string, should always be
            if not isinstance(output_name, ast.String):
                self.problems.append(
                    Problem(
                        pos=key.pos,
                        desc="Output name must be a string",
                        level=ProblemLevel.ERR,
                        rule=self.RULE_NAME,
                    )
                )
                continue

            # add output_name to job context
            outputs_context[output_name.string] = ContextType.string

    def _build_job_context_services(
        self, services_in: Dict[ast.String, Dict[ast.String, Any]], job_context: JobContext
    ) -> None:
        all_service_props = ["image", "credentials", "env", "ports", "volumes", "options"]
        for service_name, service_props in services_in.items():
            service_context = contexts.ServiceContext()

            for prop_name in service_props:
                if prop_name.string == "ports":
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
                    self.problems.append(
                        Problem(
                            pos=service_name.pos,
                            desc=f"Unknown property '{prop_name.string}' in services",
                            level=ProblemLevel.ERR,
                            rule=self.RULE_NAME,
                        )
                    )

            job_context.services.children_[service_name.string] = service_context

    def _build_runs_on(
        self, key: ast.String, runs_on_value: Any, problems: Problems, rule_name: str
    ) -> Optional[ast.RunsOn]:
        """Builds the 'runs-on' value for a job."""
        cur_pos = Pos(line=key.pos.line, col=key.pos.col)
        problem = Problem(
            pos=cur_pos, desc="Invalid 'runs-on' value", level=ProblemLevel.ERR, rule=rule_name
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
                if role == "labels":
                    labels.extend(handle_category(role, items, category.pos))
                elif role == "group":
                    group.extend(handle_category(role, items, category.pos))
                else:
                    unknown = copy.copy(problem)
                    unknown.pos = category.pos
                    unknown.desc = f"Unknown key in 'runs-on': {role}"
                    problems.append(unknown)
        else:
            problems.append(problem)
            return None

        return ast.RunsOn(pos=cur_pos, labels=labels, group=group)

    def _build_environment(
        self, key: ast.String, environment: Any, problems: Problems, rule_name: str
    ) -> Optional[ast.Environment]:
        """Builds the 'environment' value for a job."""
        if isinstance(environment, ast.String):
            return ast.Environment(pos=key.pos, name_=environment)

        if isinstance(environment, dict):
            name = environment.get("name")
            url = environment.get("url")

            if not isinstance(name, ast.String):
                problems.append(
                    Problem(
                        pos=key.pos,
                        desc=f"Invalid 'environment' 'name': '{name}'",
                        level=ProblemLevel.ERR,
                        rule=rule_name,
                    )
                )
                return None

            if url is not None:
                if not isinstance(url, ast.String):
                    problems.append(
                        Problem(
                            pos=key.pos,
                            desc=f"Invalid 'environment' 'url': '{url}'",
                            level=ProblemLevel.ERR,
                            rule=rule_name,
                        )
                    )
                    return None

            return ast.Environment(pos=key.pos, name_=name, url_=url)

        problems.append(
            Problem(
                pos=key.pos,
                desc=f"Invalid 'environment' value: '{environment}'",
                level=ProblemLevel.ERR,
                rule=rule_name,
            )
        )

        return None

    def _build_needs(self, key: ast.String, needs_value: Any) -> Optional[List[ast.String]]:
        """Build the 'needs' field for a job."""
        if needs_value is None:
            return None

        if isinstance(needs_value, ast.String):
            return [needs_value]

        if isinstance(needs_value, list):
            needs_list = []
            for item in needs_value:
                if isinstance(item, ast.String):
                    needs_list.append(item)
                else:
                    self.problems.append(
                        Problem(
                            pos=key.pos,
                            desc=(
                                f"Invalid 'needs' item: must be a string, "
                                f"got {type(item).__name__}"
                            ),
                            level=ProblemLevel.ERR,
                            rule=self.RULE_NAME,
                        )
                    )
            return needs_list if needs_list else None

        self.problems.append(
            Problem(
                pos=key.pos,
                desc=(
                    f"Invalid 'needs' value: must be a string or list of strings, "
                    f"got {type(needs_value).__name__}"
                ),
                level=ProblemLevel.ERR,
                rule=self.RULE_NAME,
            )
        )
        return None

    def _build_if(self, key: ast.String, if_value: Any) -> Optional[ast.String]:
        """Build the 'if' field for a job."""
        if if_value is None:
            return None

        if isinstance(if_value, ast.String):
            return if_value

        # Handle boolean values (like false/true)
        if isinstance(if_value, bool):
            return ast.String(str(if_value).lower(), key.pos)

        # Handle other scalar types that can be converted to string
        if isinstance(if_value, (int, float, str)):
            return ast.String(str(if_value), key.pos)

        self.problems.append(
            Problem(
                pos=key.pos,
                desc=(
                    f"Invalid 'if' value: must be a string or boolean, "
                    f"got {type(if_value).__name__}"
                ),
                level=ProblemLevel.ERR,
                rule=self.RULE_NAME,
            )
        )
        return None
