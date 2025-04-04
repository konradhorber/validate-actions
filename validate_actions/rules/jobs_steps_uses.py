import yaml
from validate_actions.lint_problem import LintProblem
from validate_actions.rules.support_functions import find_index_of, parse_action
import json
from typing import Iterator
import importlib.resources as pkg_resources

rule = 'jobs-steps-uses'

def check(tokens, schema):
    for uses_index in get_uses_indices(tokens):
        action_index = uses_index + 2
        action_slug = tokens[action_index].value
        
        yield from not_using_version_spec(action_slug, action_index, tokens)

        input_result = get_inputs(action_slug, tokens[action_index])
        if isinstance(input_result, LintProblem):
            yield input_result
            return
        else:
            required_inputs, possible_inputs = input_result

        with_index = action_index + 2
        with_token = tokens[with_index]
        with_exists = has_with(with_token)
        if not with_exists:
            if len(required_inputs) == 0:
                continue
            else:
                yield from misses_required_input(with_token, action_slug, required_inputs)
        else:
            used_inputs = list(get_used_inputs(tokens, with_index))
            yield from check_required_inputs(with_token, used_inputs, action_slug, required_inputs)
            yield from uses_non_defined_input(with_index, used_inputs, tokens, action_slug, possible_inputs)

def get_uses_indices(tokens):
    for i, token in enumerate(tokens):
        if isinstance(token, yaml.ScalarToken) and token.value == 'uses':
            yield i

def not_using_version_spec(
    action_slug: str,
    action_index: int,
    tokens: list
) -> Iterator[LintProblem]:
    if not '@' in action_slug:
       yield LintProblem(
              tokens[action_index].start_mark.line,
              tokens[action_index].start_mark.column,
              'warning',
              f'Using specific version of {action_slug} is recommended @version',
              rule
         )

def get_inputs(action_slug, action_token):
    action_metadata = parse_action(action_slug)
    if action_metadata is None:
        return LintProblem(
            action_token.start_mark.line,
            action_token.start_mark.column,
            'warning',
            f'Couldn\'t fetch metadata for {action_slug}. Continuing validation without',
            rule
        )

    inputs = action_metadata['inputs']
    possible_inputs = list(inputs.keys())
    required_inputs = [key for key, value in inputs.items() if value.get('required') is True]
    return required_inputs, possible_inputs

def has_with(token):
    return isinstance(token, yaml.ScalarToken) and token.value == 'with'

def misses_required_input(
        token: yaml.Token, 
        action_slug: str, 
        required_inputs: list) -> Iterator[LintProblem]:
    prettyprint_required_inputs = ', '.join(required_inputs)
    yield LintProblem(
        token.start_mark.line,
        token.start_mark.column,
        'error',
        f'{action_slug} misses required inputs: {prettyprint_required_inputs}',
        rule
    )

def get_used_inputs(tokens, with_index):
    i = with_index + 2
    while not isinstance(tokens[i], yaml.BlockEndToken):
        if (
            isinstance(tokens[i], yaml.KeyToken)
            and isinstance(tokens[i+1], yaml.ScalarToken)
        ):
            yield tokens[i+1].value
            i += 3
        i += 1

def check_required_inputs(with_token, used_inputs, action_slug, required_inputs):
    if len(required_inputs) == 0:
        return
            
    for input in required_inputs:
        if input not in used_inputs:
            yield from misses_required_input(with_token, action_slug, required_inputs)    


def uses_non_defined_input(with_index, used_inputs, tokens, action_slug, possible_inputs):
    if len(possible_inputs) == 0:
        return

    i = 0
    j = 4
    for input in used_inputs:
        if input not in possible_inputs:
            yield LintProblem(
                tokens[with_index + j + i * 4].start_mark.line,
                tokens[with_index + j + i * 4].start_mark.column,
                'error',
                f'{action_slug} uses unknown input: {input}',
                rule
            )
        i += 1