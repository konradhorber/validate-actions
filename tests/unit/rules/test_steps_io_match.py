# flake8: noqa: E501

from tests.conftest import parse_workflow_string
from validate_actions.globals.fixer import NoFixer
from validate_actions.globals.problems import Problem, ProblemLevel
from validate_actions.rules.steps_io_match import StepsIOMatch


def test_no_io_match():
    workflow_string = """
    name: 'Test Steps IO Match with uses'

    on: workflow_dispatch

    jobs:
      test-job:
        runs-on: ubuntu-latest
        steps:
        - id: step1
          name: 'Checkout code'
          uses: actions/checkout@v4

        - id: step2
          name: 'Upload artifact'
          uses: actions/upload-artifact@v3
          with:
            name: my-artifact
            path: ${{ steps.step1.outputs.some_output }}  # Reference to output from a uses step (which doesn't exist)
    """
    workflow, problems = parse_workflow_string(workflow_string)
    rule = StepsIOMatch(workflow, NoFixer())
    gen = rule.check()
    result = list(gen)
    assert len(result) == 1
    assert isinstance(result[0], Problem)
    assert result[0].rule == "steps-io-match"
    assert result[0].level == ProblemLevel.ERR
    assert result[0].desc == "'some_output' not as 'outputs' in 'step1'"
    assert result[0].pos.line == 18


def test_a_io_match():
    workflow_string = """
    name: 'Test Steps IO Match with uses'

    on: workflow_dispatch

    jobs:
      test-job:
        runs-on: ubuntu-latest
        steps:
        - id: step1
          name: 'Checkout code'
          uses: actions/checkout@v4

        - id: step2
          name: 'Upload artifact'
          uses: actions/upload-artifact@v3
          with:
            name: my-artifact
            path: ${{ steps.step1.outputs.ref }}
    """
    workflow, problems = parse_workflow_string(workflow_string)
    rule = StepsIOMatch(workflow, NoFixer())
    gen = rule.check()
    result = list(gen)
    assert len(result) == 0


def test_no_step_with_that_id():
    workflow_string = """
    name: 'Test Steps IO Match with uses'

    on: workflow_dispatch

    jobs:
      test-job:
        runs-on: ubuntu-latest
        steps:
        - id: step1
          name: 'Checkout code'
          uses: actions/checkout@v4

        - id: step2
          name: 'Upload artifact'
          uses: actions/upload-artifact@v3
          with:
            name: my-artifact
            path: ${{ steps.stepOne.outputs.ref }}
    """
    workflow, problems = parse_workflow_string(workflow_string)
    rule = StepsIOMatch(workflow, NoFixer())
    gen = rule.check()
    result = list(gen)
    assert len(result) == 1
    assert isinstance(result[0], Problem)
    assert result[0].rule == "steps-io-match"
    assert result[0].level == ProblemLevel.ERR
    assert (
        result[0].desc
        == "Step 'stepOne' in job 'test-job' does not exist. Available steps in this job: 'step1', 'step2'"
    )
    assert result[0].pos.line == 18
