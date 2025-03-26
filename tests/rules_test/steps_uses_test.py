import validateactions.rules.steps_uses as steps_uses
import validateactions.parser as parser
from validateactions.lint_problem import LintProblem
from validateactions import parser

# with

def test_required_input_but_no_with():
    workflow = """
name: test
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Notify Slack
        uses: 8398a7/action-slack@v3
"""
    tokens = list(parser.tokenize(workflow))
    result = steps_uses.check(tokens, None)
    assert isinstance(result, LintProblem)
    # assert result is None

def test_required_input_correct_with():
    workflow = """
name: test
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Notify Slack
        uses: 8398a7/action-slack@v3
        with: 
          status: 'test'
"""
    tokens = list(parser.tokenize(workflow))
    result = steps_uses.check(tokens, None)
    assert result is None

def test_required_input_but_wrong_with_ending_directly():
    workflow = """
name: test
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Notify Slack
        uses: 8398a7/action-slack@v3
        with: 
          fields: 'test'
"""
    tokens = list(parser.tokenize(workflow))
    result = steps_uses.check(tokens, None)
    assert isinstance(result, LintProblem)
    
def test_required_input_but_wrong_with_block_continues():
    workflow = """
name: test
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Notify Slack
        uses: 8398a7/action-slack@v3
        with: 
          fields: 'test'
      - run: npm install
"""
    tokens = list(parser.tokenize(workflow))
    result = steps_uses.check(tokens, None)
    assert isinstance(result, LintProblem)

def test_required_input_correct_with_multiple_inputs():
    workflow = """
name: test
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Notify Slack
        uses: 8398a7/action-slack@v3
        with: 
          fields: 'test'
          status: 'correct'
"""
    tokens = list(parser.tokenize(workflow))
    result = steps_uses.check(tokens, None)
    assert result is None

def test_required_input_but_wrong_multiple_inputs():
    workflow = """
name: test
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Notify Slack
        uses: 8398a7/action-slack@v3
        with: 
          fields: 'test'
          custom_payload: 'test'
"""
    tokens = list(parser.tokenize(workflow))
    result = steps_uses.check(tokens, None)
    assert isinstance(result, LintProblem)

def test_single_event_correct():
    workflow ="""
name: test 
on: push
"""
    workflow_tokens = list(parser.tokenize(workflow))
    result = steps_uses.check(workflow_tokens)
    assert isinstance(result, LintProblem)


