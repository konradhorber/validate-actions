import yaml
import linter

rule = 'event-trigger'

def check(tokens, workflow_schema):
    events = workflow_schema['definitions']['event']['enum']

    for i, token in enumerate(tokens):
        if not isinstance(token, yaml.ScalarToken):
            continue
        if not token.value == 'on':
            continue
        j = i + 2

        while (not isinstance(tokens[j], yaml.ScalarToken)):
            j += 1
        if not events.__contains__(tokens[j].value):
            desc = f'event trigger must be valid but found: "{tokens[j].value}"'
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
