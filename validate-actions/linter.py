import yaml
import json
import jsonschema
import sys

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
    def __init__(self, line, column, desc='<no description>', rule=None, level=None):
        #: Line on which the problem was found (starting at 1)
        self.line = line
        #: Column on which the problem was found (starting at 1)
        self.column = column
        #: Human-readable description of the problem
        self.desc = desc
        #: Identifier of the rule that detected the problem
        self.rule = rule
        #: Identifier of the rule that detected the problem
        self.level = level

def run(input):
    content = input.read()
    return _run(content)
    
def _run(buffer):
    try:
        with open('resources/github-workflow.json') as json_blueprint:
            workflow_schema = json.load(json_blueprint)
            workflow = yaml.load(buffer, Loader=yaml.BaseLoader)
            try:
                jsonschema.validate(workflow, workflow_schema)
            except jsonschema.exceptions.ValidationError as e:
                return [LintProblem(0,0,e.message,e.validator,PROBLEM_LEVELS[2])]
    except OSError as e:
        print(e, file=sys.stderr)
        sys.exit(-1)