import yaml
import validateactions.rules.event_trigger as event_trigger
import json
from validateactions.lint_problem import LintProblem
from validateactions import parser

SCHEMA_FILE = 'resources/github-workflow.json'
with open(SCHEMA_FILE) as f:
    schema = json.load(f)


def test_no_on():
    workflow = """
name: test
"""
    workflow_tokens = list(yaml.parse(workflow, Loader=yaml.BaseLoader))
    result = event_trigger.check(workflow_tokens, schema)
    assert isinstance(result, LintProblem)

def test_single_event_correct():
    workflow ="""
name: test 
on: push
"""
    workflow_tokens = list(parser.tokenize(workflow))
    result = event_trigger.check(workflow_tokens, schema)
    assert result is None


def test_single_event_problem():
    workflow = """
name: test 
on: ush
"""
    workflow_tokens = list(parser.tokenize(workflow))
    result = event_trigger.check(workflow_tokens, schema)
    assert isinstance(result, LintProblem)

def test_flow_sequence_correct():
    workflow ="""
name: test 
on: [push, pull_request]
"""
    workflow_tokens = list(parser.tokenize(workflow))
    result = event_trigger.check(workflow_tokens, schema)
    assert result is None

def test_flow_sequence_problem():
    workflow ="""
name: test 
on: [push, pull_equest]
"""
    workflow_tokens = list(parser.tokenize(workflow))
    result = event_trigger.check(workflow_tokens, schema)
    assert isinstance(result, LintProblem)

def test_block_sequence_correct():
    workflow ="""
name: test 
on: 
  - push
  - pull_request
"""
    workflow_tokens = list(parser.tokenize(workflow))
    result = event_trigger.check(workflow_tokens, schema)
    assert result is None

def test_block_sequence_problem():
    workflow ="""
name: test 
on: 
  - push
  - pul_request
"""
    workflow_tokens = list(parser.tokenize(workflow))
    result = event_trigger.check(workflow_tokens, schema)
    assert isinstance(result, LintProblem)

def test_block_mapping_correct():
    workflow ="""
name: test
on:
  push:
    branches: [ $default-branch ]
  pull_request:
    branches: [ $default-branch ]
"""
    workflow_tokens = list(parser.tokenize(workflow))
    result = event_trigger.check(workflow_tokens, schema)
    assert result is None

def test_block_mapping_problem():
    workflow ="""
name: test
on:
  push:
    branches: [ $default-branch ]
  pull_reuest:
    branches: [ $default-branch ]
"""
    workflow_tokens = list(parser.tokenize(workflow))
    result = event_trigger.check(workflow_tokens, schema)
    assert isinstance(result, LintProblem)
