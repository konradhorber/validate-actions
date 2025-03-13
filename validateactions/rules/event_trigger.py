import yaml
from validateactions.lint_problem import LintProblem

rule = 'event-trigger'
#TODO write tests
MATCHING_TOKENS = {
    yaml.FlowSequenceStartToken: yaml.FlowSequenceEndToken,
    yaml.BlockSequenceStartToken: yaml.BlockEndToken,
    yaml.BlockMappingStartToken: yaml.BlockEndToken,
    yaml.FlowMappingStartToken: yaml.FlowMappingEndToken
}

def check(tokens, schema):
    on_index = find_on_index(tokens)
    if not on_index:
        return LintProblem(0, 0, 'error', 'No on token found', rule)

    structure_determining_token_index = on_index + 2
    structure = type(tokens[structure_determining_token_index])

    match structure:
        case yaml.ScalarToken:
            return check_single_event(tokens, schema, structure_determining_token_index)
        case yaml.FlowSequenceStartToken:
            return check_sequence(tokens, schema, structure_determining_token_index, MATCHING_TOKENS[structure])
        case yaml.BlockSequenceStartToken:
            return check_sequence(tokens, schema, structure_determining_token_index, MATCHING_TOKENS[structure])
        case yaml.BlockMappingStartToken:
            return check_mapping(tokens, schema, structure_determining_token_index, MATCHING_TOKENS[structure])
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
        if not isinstance(token, yaml.ScalarToken):
            continue
        if not token.value == 'on':
            continue
        return i
    return

def check_single_event(tokens, schema, structure_determining_token_index):
    event_index = structure_determining_token_index
    token = tokens[event_index]
    return check_scalar_against_schema(token, schema)

def check_sequence(tokens, schema, structure_determining_token_index, end_token):
    i = structure_determining_token_index + 1

    token = tokens[i]
    while (not isinstance(token, end_token)):
        if isinstance(token, yaml.ScalarToken):
            problem = check_scalar_against_schema(token, schema)
            if problem:
                return problem
        i += 1
        token = tokens[i]
    return None

def check_mapping(tokens, schema, structure_determining_token_index, end_token):
    i = structure_determining_token_index + 1

    token = tokens[i]

    while (not isinstance(token, end_token)):
        if isinstance(token, yaml.ScalarToken):
            problem = check_scalar_against_schema(token, schema)
            if problem:
                return problem
        elif type(token) in MATCHING_TOKENS.keys():
            brace_type = type(token)
            while (not isinstance(token, MATCHING_TOKENS[brace_type])):
                i += 1
                token = tokens[i]

        i += 1
        token = tokens[i]
    return None

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
    return

def parse_events_from_schema(schema):
    events = []
    for event in schema['definitions']['event']['enum']:
        events.append(event)
    return events