# flake8: noqa: E501

from tests.helper import parse_workflow_string
from validate_actions import LintProblem, rules


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
    gen = rules.StepsIOMatch.check(workflow)
    result = list(gen)
    assert len(result) == 1
    assert isinstance(result[0], LintProblem)
    assert result[0].rule == 'steps-io-match'
    assert result[0].level == 'error'
    assert result[0].desc == "'some_output' not as 'outputs' in 'step1'"
    assert result[0].line == 18


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
    gen = rules.StepsIOMatch.check(workflow)
    result = list(gen)
    assert len(result) == 0
