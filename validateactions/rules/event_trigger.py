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
    on_indices = list(find_index_of('on', yaml.ScalarToken, tokens))
    if len(on_indices) == 1:
        on_index = on_indices[0]
        structure_determining_token_index = on_index + 2
    elif not on_indices:
        yield LintProblem(0, 0, 'error', 'No "on" token found', rule)
        return
    else:
        yield LintProblem(0, 0, 'error', 'Multiple "on" tokens found', rule)
        return
    structure = type(tokens[structure_determining_token_index])

    events = parse_events_from_schema(schema)

    match structure:
        case yaml.ScalarToken:
            yield from check_single_event(tokens, events, structure_determining_token_index)
        case yaml.FlowSequenceStartToken:
            yield from check_sequence(tokens, events, structure_determining_token_index, MATCHING_TOKENS[structure])
        case yaml.BlockSequenceStartToken:
            yield from check_sequence(tokens, events, structure_determining_token_index, MATCHING_TOKENS[structure])
        case yaml.BlockMappingStartToken:
            yield from check_mapping(tokens, events, structure_determining_token_index, MATCHING_TOKENS[structure])
        case yaml.FlowMappingStartToken:
            return # TODO
        case _:
            error_token = tokens[structure_determining_token_index]
            yield LintProblem(
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

def check_single_event(tokens, events, structure_determining_token_index):
    event_index = structure_determining_token_index
    token = tokens[event_index]
    yield from check_scalar_against_schema(token, events)

def check_sequence(tokens, events, structure_determining_token_index, end_token):
    i = structure_determining_token_index + 1

    token = tokens[i]
    while (not isinstance(token, end_token)):
        if isinstance(token, yaml.ScalarToken):
            yield from check_scalar_against_schema(token, events)
        i += 1
        token = tokens[i]

def check_mapping(tokens, events, structure_determining_token_index, end_token):
    i = structure_determining_token_index + 1

    token = tokens[i]
    
    while (not isinstance(token, end_token)):
        if isinstance(token, yaml.ScalarToken):
            yield from check_scalar_against_schema(token, events)
        elif type(token) in MATCHING_TOKENS.keys():
            brace_type = type(token)
            while (not isinstance(token, MATCHING_TOKENS[brace_type])):
                i += 1
                token = tokens[i]

        i += 1
        token = tokens[i]

def check_scalar_against_schema(token, events):
    event = token
    if not event.value in events:
        desc = f'event must be valid but found: "{event.value}"'
        level = 'error'
        yield LintProblem(
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