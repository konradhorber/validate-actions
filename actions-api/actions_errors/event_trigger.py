import yaml
import linter

rule = 'event-trigger'

event_triggers = [
    'push',
    'pull_request',
    'schedule',
    'workflow_dispatch',
    'repository_dispatch',
]

def check(tokens):
    for i, token in enumerate(tokens):
        if isinstance(token.curr, yaml.ScalarToken) and token.curr.value == 'on':
            j = i + 2
            while (not isinstance(tokens[j].curr, yaml.ScalarToken)):
                j += 1
            if not event_triggers.__contains__(tokens[j].curr.value):
                desc = f'Event trigger must be valid but found: "{tokens[j].curr.value}"'
                problem = linter.LintProblem(
                    tokens[j].curr.start_mark.line + 1,
                    tokens[j].curr.start_mark.column + 1,
                    desc,
                    rule
                )
                problem.level = 'error'
                return problem
            # TODO think about how to use indentation to read
            return
