from tests.helper import parse_workflow_string
from validate_actions import LintProblem, rules


# with
def test_unknown_action_throws_warning():
    workflow_string = """
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
    workflow, problems = parse_workflow_string(workflow_string)
    gen = rules.JobsStepsUses.check(workflow)
    result = list(gen)
    assert len(result) == 1
    assert isinstance(result[0], LintProblem)
    assert result[0].rule == 'jobs-steps-uses'
    assert result[0].level == 'warning'


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
    throws_single_error(workflow)


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
    throws_no_error(workflow)


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
    throws_single_error(workflow)


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
    throws_single_error(workflow)


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
    throws_no_error(workflow)


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
    throws_single_error(workflow)
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
    throws_no_error(workflow)


def test_uses_non_existent_input_first():
    workflow_string = """
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
    workflow, problems = parse_workflow_string(workflow_string)
    gen = rules.JobsStepsUses.check(workflow)
    result = list(gen)
    assert len(result) == 1
    assert isinstance(result[0], LintProblem)
    assert result[0].rule == 'jobs-steps-uses'
    assert result[0].line == 7
    assert result[0].desc == "8398a7/action-slack@v2 uses unknown input: wrong_input"


def test_uses_non_existent_input_second():
    workflow_string = """
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
    workflow, problems = parse_workflow_string(workflow_string)
    gen = rules.JobsStepsUses.check(workflow)
    result = list(gen)
    assert len(result) == 1
    assert isinstance(result[0], LintProblem)
    assert result[0].rule == 'jobs-steps-uses'
    assert result[0].line == 7
    assert result[0].desc == "8398a7/action-slack@v2 uses unknown input: wrong_input"

# endregion all inputs


def throws_single_error(workflow_string: str):
    workflow, problems = parse_workflow_string(workflow_string)
    gen = rules.JobsStepsUses.check(workflow)
    result = list(gen)
    assert len(result) == 1
    assert isinstance(result[0], LintProblem)
    assert result[0].rule == 'jobs-steps-uses'


def throws_no_error(workflow_string: str):
    workflow, problems = parse_workflow_string(workflow_string)
    gen = rules.JobsStepsUses.check(workflow)
    result = list(gen)
    assert result == []
