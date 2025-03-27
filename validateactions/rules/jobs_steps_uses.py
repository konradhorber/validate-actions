import yaml
from validateactions.lint_problem import LintProblem
from validateactions.rules.support_functions import find_index_of
import json
from typing import Iterator

rule = 'jobs-steps-uses'

def check(tokens, schema):
    for uses_index in get_uses_indices(tokens):
        action_index = uses_index + 2
        action_slug = tokens[action_index].value
        
        yield from not_using_version_spec(action_slug, action_index, tokens)

        required_inputs, possible_inputs = get_inputs(action_slug)

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

def get_inputs(action_slug):
    with open('resources/popular_actions.json', 'r') as f:
        popular_actions = json.load(f)

        try:
            action_schema = popular_actions[action_slug]
        except KeyError:
            return [], []

        required_inputs = []
        possible_inputs = []
        for input, required in action_schema['inputs'].items():
            if required == True:
                required_inputs.append(input)
                possible_inputs.append(input)
            else:
                possible_inputs.append(input)
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