import yaml
import validate_actions.rules.event_trigger as event_trigger
import json
from validate_actions.lint_problem import LintProblem
from validate_actions import parser
import importlib.resources as pkg_resources

SCHEMA_FILE = 'github-workflow.json'
schema_path = pkg_resources.files('validate_actions.resources').joinpath(SCHEMA_FILE)
with schema_path.open('r', encoding='utf-8') as f:
    schema = json.load(f)


def test_no_on():
    workflow = """
name: test
"""
    workflow_tokens = list(yaml.parse(workflow, Loader=yaml.BaseLoader))
    gen = event_trigger.check(workflow_tokens, schema)
    result = list(gen)
    assert len(result) == 1
    assert isinstance(result[0], LintProblem)
    assert result[0].rule == 'event-trigger'

def test_single_event_correct():
    workflow ="""
name: test 
on: push
"""
    workflow_tokens = list(parser.tokenize(workflow))
    gen = event_trigger.check(workflow_tokens, schema)
    result = list(gen)
    assert result == []


def test_single_event_problem():
    workflow = """
name: test 
on: ush
"""
    workflow_tokens = list(parser.tokenize(workflow))
    gen = event_trigger.check(workflow_tokens, schema)
    result = list(gen)
    assert len(result) == 1
    assert isinstance(result[0], LintProblem)
    assert result[0].rule == 'event-trigger'

def test_flow_sequence_correct():
    workflow ="""
name: test 
on: [push, pull_request]
"""
    workflow_tokens = list(parser.tokenize(workflow))
    gen = event_trigger.check(workflow_tokens, schema)
    result = list(gen)
    assert result == []

def test_flow_sequence_problem():
    workflow ="""
name: test 
on: [push, pull_equest]
"""
    workflow_tokens = list(parser.tokenize(workflow))
    gen = event_trigger.check(workflow_tokens, schema)
    result = list(gen)
    assert len(result) == 1
    assert isinstance(result[0], LintProblem)
    assert result[0].rule == 'event-trigger'

def test_block_sequence_correct():
    workflow ="""
name: test 
on: 
  - push
  - pull_request
"""
    workflow_tokens = list(parser.tokenize(workflow))
    gen = event_trigger.check(workflow_tokens, schema)
    result = list(gen)
    assert result == []

def test_block_sequence_problem():
    workflow ="""
name: test 
on: 
  - push
  - pul_request
"""
    workflow_tokens = list(parser.tokenize(workflow))
    gen = event_trigger.check(workflow_tokens, schema)
    result = list(gen)
    assert len(result) == 1
    assert isinstance(result[0], LintProblem)
    assert result[0].rule == 'event-trigger'

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
    gen = event_trigger.check(workflow_tokens, schema)
    result = list(gen)
    assert result == []

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
    gen = event_trigger.check(workflow_tokens, schema)
    result = list(gen)
    assert len(result) == 1
    assert isinstance(result[0], LintProblem)
    assert result[0].rule == 'event-trigger'
