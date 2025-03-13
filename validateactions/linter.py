import yaml
import parser
import json
import rules.event_trigger as event_trigger
from lint_problem import LintProblem

PROBLEM_LEVELS = {
    0: None,
    1: 'warning',
    2: 'error',
    None: 0,
    'warning': 1,
    'error': 2,
}

SCHEMA_FILE = 'resources/github-workflow.json'

def run(input):
    content = input.read()
    return _run(content)
    
# TODO think about how to get multiple errors
def _run(buffer):
    syntax_error = get_syntax_error(buffer)
    actions_error = get_actions_error(buffer)

    if syntax_error:
        yield syntax_error
    
    if actions_error:
        yield actions_error

def get_syntax_error(buffer):
    assert hasattr(buffer, '__getitem__'), \
        '_run() argument must be a buffer, to be parsed multiple times. Not a stream'
    try:
        list(yaml.parse(buffer, Loader=yaml.BaseLoader))
    except yaml.error.MarkedYAMLError as e:
        return LintProblem(e.problem_mark.line,
                           e.problem_mark.column,
                           'error',
                           'syntax error: ' + e.problem,
                           'syntax')

actions_errors = [event_trigger]

def get_actions_error(buffer):
    tokens = list(parser.tokenize(buffer))
    schema = get_workflow_schema(SCHEMA_FILE)
    for error in actions_errors:
        problem = error.check(tokens, schema)
        if problem:
            return problem
        
def get_workflow_schema(file):
    with open(file) as f:
        return json.load(f)