import yaml
import linter

rule = 'event-trigger'

def check(tokens, schema):
    for i, token in enumerate(tokens):
        if not isinstance(token, yaml.ScalarToken):
            continue
        if not token.value == 'on':
            continue
        j = i + 2

        while (not isinstance(tokens[j], yaml.ScalarToken)):
            j += 1
        
        events = parse_events_from_schema(schema)

        if not events.__contains__(tokens[j].value):
            desc = f'event must be valid but found: "{tokens[j].value}"'
            problem = linter.LintProblem(
                tokens[j].start_mark.line,
                tokens[j].start_mark.column,
                desc,
                rule
            )
            problem.level = 'error'
            return problem
        # TODO think about how to use indentation to read
        return
    
def parse_events_from_schema(schema):
    events = []
    for event in schema['definitions']['event']['enum']:
        events.append(event)
    return events