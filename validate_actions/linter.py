import yaml
import validate_actions.parser as parser
import json
import validate_actions.rules as rules
from validate_actions.lint_problem import LintProblem
import importlib.resources as pkg_resources

PROBLEM_LEVELS = {
    0: None,
    1: 'warning',
    2: 'error',
    None: 0,
    'warning': 1,
    'error': 2,
}

def run(input):
    content = input.read()
    return _run(content)
    
def _run(buffer):
    l = list(get_actions_error(buffer))
    for problem in l:
        if problem == None:
            l.remove(problem)
    syntax_error = get_syntax_error(buffer)
    if syntax_error:
        l.append(syntax_error)
    return l

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

ACTIONS_ERROR_RULES = [
    rules.jobs_steps_uses,
    rules.event_trigger,
    ]

def get_actions_error(buffer):
    tokens = list(parser.tokenize(buffer))
    schema = get_workflow_schema('github-workflow.json')
    for rule in ACTIONS_ERROR_RULES:
        yield from rule.check(tokens, schema)
        
def get_workflow_schema(file):
    with pkg_resources.open_text('validate_actions.resources', file) as f:
        return json.load(f)