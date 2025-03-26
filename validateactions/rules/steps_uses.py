import yaml
from validateactions.lint_problem import LintProblem
from validateactions.rules.support_functions import find_index_of
import json
from typing import Iterator

rule = 'steps-uses'

def check(tokens, schema):
    uses_index = find_index_of('uses', yaml.ScalarToken, tokens) # yaml.events.ScalarEvent
    if uses_index == -1:
        return None
    
    action_index = uses_index + 2
    action_slug = tokens[action_index].value
    # yield not_using_version_spec(action_slug, action_index, tokens) TODO

    required_inputs, optional_inputs = get_inputs(action_slug)
    # fix what if no inputs found
    return check_required_inputs(action_index, tokens, action_slug, required_inputs)


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
              'Using specific version of the action is recommended (e.g., @v2)',
              rule
         )
       
def get_inputs(action_slug):
    with open('resources/popular_actions.json', 'r') as f:
        popular_actions = json.load(f)
    
        action_schema = popular_actions[action_slug]
        if action_schema == None:
            return None
        
        required_inputs = []
        optional_inputs = []
        for input, required in action_schema['inputs'].items():
            if required == True:
                required_inputs.append(input)
            else:
                optional_inputs.append(input)
        return required_inputs, optional_inputs
       
def check_required_inputs(action_index, tokens, action_slug,required_inputs):
    if len(required_inputs) == 0:
        return None
    
    with_index = action_index + 2
    problems = []
    problems.append(has_no_with(tokens[with_index], action_slug, required_inputs))
    problems.append(has_wrong_with(tokens, with_index, action_slug, required_inputs))

    for problem in problems:
        if problem is not None:
            return problem

def has_no_with(token, action_slug, required_inputs):
    if (
        isinstance(token, yaml.ScalarToken) 
        and token.value == 'with'
    ):
        return None
    return return_missing_inputs_problem(token, action_slug, required_inputs)

def has_wrong_with(tokens, with_index, action_slug, required_inputs):
    block_start_index = with_index + 2
    
    used_inputs = {}
    i = block_start_index
    while not isinstance(tokens[i], yaml.BlockEndToken):
        if (
            isinstance(tokens[i], yaml.KeyToken)
            and isinstance(tokens[i+1], yaml.ScalarToken)
        ):
            used_inputs.update({tokens[i+1].value: tokens[i+3].value})
            i += 3
        i += 1
    
    for input in required_inputs:
        if input not in used_inputs:
            return return_missing_inputs_problem(tokens[with_index], action_slug, required_inputs)

def return_missing_inputs_problem(
        token: yaml.Token, 
        action_slug: str, 
        required_inputs: list) -> LintProblem:
    prettyprint_required_inputs = ', '.join(required_inputs)
    return LintProblem(
        token.start_mark.line,
        token.start_mark.column,
        'error',
        f'{action_slug} misses required inputs: {prettyprint_required_inputs}',
        rule
    )