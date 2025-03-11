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
    def __init__(self, location, desc='<no description>', rule=None, level=None):
        #: Location where this problem occured
        self.location = location
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
                problem_path = "".join(f"{item}:" for item in e.absolute_path)
                return [LintProblem(problem_path,e.message,e.validator,PROBLEM_LEVELS[2])]
            return []
    except OSError as e:
        print(e, file=sys.stderr)
        sys.exit(-1)