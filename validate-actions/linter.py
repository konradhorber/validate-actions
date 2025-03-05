import yaml
import parser
import actions_errors.event_trigger as event_trigger

PROBLEM_LEVELS = {
    0: None,
    1: 'warning',
    2: 'error',
    None: 0,
    'warning': 1,
    'error': 2,
}

class LintProblem:
    """Represents a linting problem"""
    def __init__(self, line, column, desc='<no description>', rule=None):
        #: Line on which the problem was found (starting at 1)
        self.line = line
        #: Column on which the problem was found (starting at 1)
        self.column = column
        #: Human-readable description of the problem
        self.desc = desc
        #: Identifier of the rule that detected the problem
        self.rule = rule
        #: Identifier of the rule that detected the problem
        self.level = None

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
        problem = LintProblem(e.problem_mark.line + 1,
                              e.problem_mark.column + 1,
                              'syntax error: ' + e.problem,
                              'syntax')
        problem.level = 'error'
        return problem

actions_errors = [event_trigger]

def get_actions_error(buffer):
    tokens = list(parser.tokenize(buffer))
    for error in actions_errors:
        problem = error.check(tokens)
        if problem:
            return problem