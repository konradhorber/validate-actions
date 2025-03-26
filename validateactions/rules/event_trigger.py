import yaml
from validateactions.lint_problem import LintProblem
from validateactions.rules.support_functions import find_index_of

rule = 'event-trigger'

MATCHING_TOKENS = {
    yaml.FlowSequenceStartToken: yaml.FlowSequenceEndToken,
    yaml.BlockSequenceStartToken: yaml.BlockEndToken,
    yaml.BlockMappingStartToken: yaml.BlockEndToken,
    yaml.FlowMappingStartToken: yaml.FlowMappingEndToken
}

def check(tokens, schema):
    on_index = find_index_of('on', yaml.ScalarToken, tokens)
    if not on_index:
        return LintProblem(0, 0, 'error', 'No on token found', rule)

    structure_determining_token_index = on_index + 2
    structure = type(tokens[structure_determining_token_index])

    match structure:
        case yaml.ScalarToken:
            return check_single_event(tokens, schema, structure_determining_token_index)
        case yaml.FlowSequenceStartToken:
            yield from check_sequence(tokens, schema, structure_determining_token_index, MATCHING_TOKENS[structure])
        case yaml.BlockSequenceStartToken:
            yield from check_sequence(tokens, schema, structure_determining_token_index, MATCHING_TOKENS[structure])
        case yaml.BlockMappingStartToken:
            yield from check_mapping(tokens, schema, structure_determining_token_index, MATCHING_TOKENS[structure])
        case yaml.FlowMappingStartToken:
            return # TODO
        case _:
            error_token = tokens[structure_determining_token_index]
            return LintProblem(
                error_token.start_mark.line,
                error_token.start_mark.column,
                'error',
                'Invalid structure after on:',
                rule
            )
    
def find_on_index(tokens):
    for i, token in enumerate(tokens):
        if isinstance(token, yaml.ScalarToken) and token.value == 'on':
            return i

def check_single_event(tokens, schema, structure_determining_token_index):
    event_index = structure_determining_token_index
    token = tokens[event_index]
    return check_scalar_against_schema(token, schema)

def check_sequence(tokens, schema, structure_determining_token_index, end_token):
    i = structure_determining_token_index + 1

    token = tokens[i]
    while (not isinstance(token, end_token)):
        if isinstance(token, yaml.ScalarToken):
            yield check_scalar_against_schema(token, schema)
        i += 1
        token = tokens[i]

def check_mapping(tokens, schema, structure_determining_token_index, end_token):
    i = structure_determining_token_index + 1

    token = tokens[i]

    while (not isinstance(token, end_token)):
        if isinstance(token, yaml.ScalarToken):
            yield check_scalar_against_schema(token, schema)
        elif type(token) in MATCHING_TOKENS.keys():
            brace_type = type(token)
            while (not isinstance(token, MATCHING_TOKENS[brace_type])):
                i += 1
                token = tokens[i]

        i += 1
        token = tokens[i]

def check_scalar_against_schema(token, schema):
    events = parse_events_from_schema(schema)
    event = token
    if not events.__contains__(event.value):
        desc = f'event must be valid but found: "{event.value}"'
        level = 'error'
        return LintProblem(
            event.start_mark.line,
            event.start_mark.column,
            level,
            desc,
            rule
        )

def parse_events_from_schema(schema):
    events = []
    for event in schema['definitions']['event']['enum']:
        events.append(event)
    return events