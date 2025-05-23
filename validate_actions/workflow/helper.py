import dataclasses
import importlib.resources as pkg_resources
import json
from typing import Any, Dict, Optional, Union

from validate_actions.pos import Pos
from validate_actions.problems import Problem, ProblemLevel, Problems
from validate_actions.workflow import ast


def build_env(
    env_vars: Dict[ast.String, Any],
    problems: Problems,
    RULE_NAME: str
) -> Optional[ast.Env]:
    env_vars_out: Dict[ast.String, ast.String] = {}
    for key in env_vars:
        if isinstance(key, ast.String) and isinstance(env_vars[key], ast.String):
            env_vars_out[key] = env_vars[key]
        else:
            problems.append(Problem(
                pos=key.pos,
                desc=f"Invalid environment variable value: {key.string}",
                level=ProblemLevel.ERR,
                rule=RULE_NAME
            ))
    if len(env_vars_out) == 0:
        problems.append(Problem(
            pos=Pos(0, 0),
            desc="No valid environment variables found.",
            level=ProblemLevel.ERR,
            rule=RULE_NAME
        ))
        return None
    return ast.Env(env_vars_out)


def build_permissions(
    permissions_in: Union[Dict[ast.String, Any], ast.String],
    problems: Problems,
    RULE_NAME: str
) -> ast.Permissions:
    permissions_data = {}
    possible_permission_fields = {field.name for field in dataclasses.fields(ast.Permissions)}

    if isinstance(permissions_in, ast.String):
        if permissions_in.string == "read-all":
            permission_value = ast.Permission.read
        elif permissions_in.string == "write-all":
            permission_value = ast.Permission.write
        else:
            problems.append(Problem(
                pos=permissions_in.pos,
                desc=f"Invalid permission value: {permissions_in.string}",
                level=ProblemLevel.ERR,
                rule=RULE_NAME
            ))
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
                    problems.append(Problem(
                        pos=key.pos,
                        desc=f"Invalid permission value: {val.string}",
                        level=ProblemLevel.ERR,
                        rule=RULE_NAME
                    ))
                    continue

                if key_str_conv not in possible_permission_fields:
                    problems.append(Problem(
                        pos=key.pos,
                        desc=f"Invalid permission: {key.string}",
                        level=ProblemLevel.ERR,
                        rule=RULE_NAME
                    ))
                    continue

                permissions_data[key_str_conv] = permission
            else:
                problems.append(Problem(
                    pos=key.pos,
                    desc="Invalid permission",
                    level=ProblemLevel.ERR,
                    rule=RULE_NAME
                ))

    return ast.Permissions(**permissions_data)


def get_workflow_schema(file: str) -> dict:
    schema_path = pkg_resources.files(
        'validate_actions.resources'
    ).joinpath(file)
    with schema_path.open('r', encoding='utf-8') as f:
        return json.load(f)


def convert_string(input_string: str) -> str:
    """
    Converts hyphens to underscores in a string and adds an underscore to the end.
    """
    return input_string.replace('-', '_') + '_'
