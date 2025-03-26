import validateactions.rules.jobs_steps_uses as jobs_steps_uses
import validateactions.parser as parser
from validateactions.lint_problem import LintProblem
from validateactions import parser

# with
def test_unknown_action_passes():
    workflow = """
name: test
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Notify Slack
        uses: action/is-unknown@vtest
        with:
          unknown_input: 'test'
"""
    tokens = list(parser.tokenize(workflow))
    result = jobs_steps_uses.check(tokens, None)
    assert result is None


# region required inputs
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
    result = jobs_steps_uses.check(tokens, None)
    assert isinstance(result, LintProblem)

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
    result = jobs_steps_uses.check(tokens, None)
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
    result = jobs_steps_uses.check(tokens, None)
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
    result = jobs_steps_uses.check(tokens, None)
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
    result = jobs_steps_uses.check(tokens, None)
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
    result = jobs_steps_uses.check(tokens, None)
    assert isinstance(result, LintProblem)

# endregion required inputs

# region all inputs
def test_uses_existent_optional_input():
    workflow = """
name: test
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Notify Slack
        uses: 8398a7/action-slack@v2
        with: 
          status: 'test'
"""
    tokens = list(parser.tokenize(workflow))
    result = jobs_steps_uses.check(tokens, None)
    assert result is None

def test_uses_non_existent_input_first():
    workflow = """
name: test
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Notify Slack
        uses: 8398a7/action-slack@v2
        with: 
          wrong_input: 'test'
          status: 'test'
"""
    tokens = list(parser.tokenize(workflow))
    result = jobs_steps_uses.check(tokens, None)
    assert isinstance(result, LintProblem)
    assert result.line == 9
    assert result.desc == "8398a7/action-slack@v2 has unknown input: wrong_input"

def test_uses_non_existent_input_second():
    workflow = """
name: test
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Notify Slack
        uses: 8398a7/action-slack@v2
        with: 
          status: 'test'
          wrong_input: 'test'
"""
    tokens = list(parser.tokenize(workflow))
    result = jobs_steps_uses.check(tokens, None)
    assert isinstance(result, LintProblem)
    assert result.line == 10
    assert result.desc == "8398a7/action-slack@v2 has unknown input: wrong_input"

# endregion all inputs

