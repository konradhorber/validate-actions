import copy
import dataclasses
import importlib.resources as pkg_resources
import json
from typing import Any, Dict, Optional, Union

from validate_actions.pos import Pos
from validate_actions.problems import Problem, ProblemLevel, Problems
from validate_actions.workflow import ast


def build_env(
    env_vars: Dict[ast.String, Any], problems: Problems, RULE_NAME: str
) -> Optional[ast.Env]:
    env_vars_out: Dict[ast.String, ast.String] = {}
    for key in env_vars:
        if isinstance(key, ast.String):
            value = env_vars[key]
            if isinstance(value, ast.String):
                env_vars_out[key] = value
            elif isinstance(value, bool):
                # Convert boolean to string
                string_value = ast.String(str(value).lower(), key.pos)
                env_vars_out[key] = string_value
            elif isinstance(value, int):
                # Convert integer to string
                string_value = ast.String(str(value), key.pos)
                env_vars_out[key] = string_value
            else:
                problems.append(
                    Problem(
                        pos=key.pos,
                        desc=f"Invalid environment variable value: {key.string}",
                        level=ProblemLevel.ERR,
                        rule=RULE_NAME,
                    )
                )
        else:
            problems.append(
                Problem(
                    pos=key.pos,
                    desc="Invalid environment variable value",
                    level=ProblemLevel.ERR,
                    rule=RULE_NAME,
                )
            )
    if len(env_vars_out) == 0:
        problems.append(
            Problem(
                pos=Pos(0, 0),
                desc="No valid environment variables found",
                level=ProblemLevel.ERR,
                rule=RULE_NAME,
            )
        )
        return None
    return ast.Env(env_vars_out)


def build_permissions(
    permissions_in: Union[Dict[ast.String, Any], ast.String], problems: Problems, RULE_NAME: str
) -> ast.Permissions:
    permissions_data = {}
    possible_permission_fields = {field.name for field in dataclasses.fields(ast.Permissions)}

    if isinstance(permissions_in, ast.String):
        if permissions_in.string == "read-all":
            permission_value = ast.Permission.read
        elif permissions_in.string == "write-all":
            permission_value = ast.Permission.write
        else:
            problems.append(
                Problem(
                    pos=permissions_in.pos,
                    desc=f"Invalid permission value: {permissions_in.string}",
                    level=ProblemLevel.ERR,
                    rule=RULE_NAME,
                )
            )
            return ast.Permissions()

        if permission_value:
            for field in dataclasses.fields(ast.Permissions):
                permissions_data[field.name] = permission_value

    elif isinstance(permissions_in, dict):
        if len(permissions_in) == 0:
            for possible_permission_field in possible_permission_fields:
                permissions_data[possible_permission_field] = ast.Permission.none
        for key in permissions_in:
            val = permissions_in[key]
            if isinstance(key, ast.String) and isinstance(val, ast.String):
                key_str_conv = convert_string(key.string)

                try:
                    permission = ast.Permission[val.string]
                except KeyError:
                    problems.append(
                        Problem(
                            pos=key.pos,
                            desc=f"Invalid permission value: {val.string}",
                            level=ProblemLevel.ERR,
                            rule=RULE_NAME,
                        )
                    )
                    continue

                if key_str_conv not in possible_permission_fields:
                    problems.append(
                        Problem(
                            pos=key.pos,
                            desc=f"Invalid permission: {key.string}",
                            level=ProblemLevel.ERR,
                            rule=RULE_NAME,
                        )
                    )
                    continue

                permissions_data[key_str_conv] = permission
            else:
                problems.append(
                    Problem(
                        pos=key.pos,
                        desc="Invalid permission",
                        level=ProblemLevel.ERR,
                        rule=RULE_NAME,
                    )
                )

    return ast.Permissions(**permissions_data)


def build_defaults(
    defaults_dict: Dict[ast.String, Dict[ast.String, Dict[ast.String, ast.String]]],
    problems: Problems,
    RULE_NAME: str,
) -> Optional[ast.Defaults]:
    shell_: Optional[ast.Shell] = None
    working_directory_: Optional[ast.String] = None
    current_pos = Pos(0, 0)
    base_problem = Problem(
        pos=current_pos,
        desc="Invalid 'defaults:' structure.",
        level=ProblemLevel.ERR,
        rule=RULE_NAME,
    )

    # Validate the structure of the defaults dictionary
    if (
        not isinstance(defaults_dict, dict)
        or not all(isinstance(k, ast.String) for k in defaults_dict.keys())
        or len(defaults_dict) != 1
    ):
        problems.append(base_problem)
        return None

    # Extract the run key and its position
    run_key = next(iter(defaults_dict.keys()))
    current_pos = run_key.pos
    run_dict = defaults_dict[run_key]

    # Validate the run key and its value
    if (
        not isinstance(run_dict, dict)
        or not run_key.string == "run"
        or not all(isinstance(k, ast.String) for k in run_dict.keys())
    ):
        problems.append(base_problem)
        return None

    # Build and validate the contents of the run dictionary
    for key, value in run_dict.items():
        match key.string:
            case "shell":
                if isinstance(value, ast.String):
                    if value.string in {shell.value for shell in ast.Shell}:
                        shell_ = ast.Shell(value.string)
                    else:
                        problems.append(
                            Problem(
                                pos=value.pos,
                                desc=f"Invalid shell: {value.string}",
                                level=ProblemLevel.ERR,
                                rule=RULE_NAME,
                            )
                        )
                else:
                    problems.append(
                        Problem(
                            pos=key.pos,
                            desc="Format error in 'defaults: run: shell'",
                            level=ProblemLevel.ERR,
                            rule=RULE_NAME,
                        )
                    )
            case "working-directory":
                if isinstance(value, ast.String):
                    working_directory_ = value
                else:
                    problems.append(
                        Problem(
                            pos=key.pos,
                            desc="Format error in 'defaults: run: working-directory'",
                            level=ProblemLevel.ERR,
                            rule=RULE_NAME,
                        )
                    )
            case _:
                problems.append(
                    Problem(
                        pos=key.pos,
                        desc=f"Format error in 'defaults: run: {key.string}'",
                        level=ProblemLevel.ERR,
                        rule=RULE_NAME,
                    )
                )

    # If no shell or working directory is specified, return None
    if shell_ is None and working_directory_ is None:
        return None

    # If we reach here, we have valid shell and/or working directory
    return ast.Defaults(
        pos=current_pos,
        shell_=shell_,
        working_directory_=working_directory_,
    )


def build_concurrency(
    key: ast.String,
    concurrency_in: Dict[ast.String | str, ast.String],
    problems: Problems,
    RULE_NAME: str,
) -> Optional[ast.Concurrency]:
    problem = Problem(
        pos=key.pos,
        desc="Invalid 'concurrency' structure.",
        level=ProblemLevel.ERR,
        rule=RULE_NAME,
    )

    if not isinstance(concurrency_in, dict):
        problems.append(problem)
        return None

    group = concurrency_in.get("group")
    concurrency_in.pop("group", None)

    cancel_in_progress = concurrency_in.get("cancel-in-progress", None)
    concurrency_in.pop("cancel-in-progress", None)

    if len(concurrency_in) > 0:
        item = next(iter(concurrency_in))
        cur_problem = copy.copy(problem)
        if isinstance(item, ast.String):
            pos = item.pos
            cur_problem.pos = pos
        problems.append(cur_problem)

    if not isinstance(group, ast.String):
        cur_problem = copy.copy(problem)
        cur_problem.desc = "Concurrency must define 'group'"
        problems.append(cur_problem)
        return None

    cur_problem = copy.copy(problem)
    cur_problem.desc = "Invalid 'concurrency' 'cancel-in-progress' value"
    if isinstance(cancel_in_progress, ast.String):
        if not cancel_in_progress.expr:
            cur_problem.pos = cancel_in_progress.pos
            problems.append(cur_problem)
            cancel_in_progress = None
    elif cancel_in_progress is not None and not isinstance(cancel_in_progress, bool):
        problems.append(cur_problem)
        cancel_in_progress = None

    return ast.Concurrency(pos=key.pos, group_=group, cancel_in_progress_=cancel_in_progress)


def get_workflow_schema(file: str) -> dict:
    schema_path = pkg_resources.files("validate_actions.resources").joinpath(file)
    with schema_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def convert_string(input_string: str) -> str:
    """
    Converts hyphens to underscores in a string and adds an underscore to the end.
    """
    return input_string.replace("-", "_") + "_"
