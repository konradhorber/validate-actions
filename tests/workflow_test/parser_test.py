from tests.helper import parse_workflow_string
from validate_actions.domain_model.pos import Pos
from validate_actions.domain_model import ast


def test_parse_str_to_ref():
    workflow_string = """
on: push
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
          name: ${{ steps.step1.outputs.ref }}
"""
    workflow, problems = parse_workflow_string(workflow_string)
    ref = workflow.jobs_["test-job"].steps_[1].exec.with_["name"]
    parts = [
        "steps",
        "step1",
        "outputs",
        "ref",
    ]
    should_be = ast.String(
        pos=Pos(line=14, col=16),
        string="${{ steps.step1.outputs.ref }}",
        expr=[
            ast.Expression(
                pos=Pos(line=14, col=16),
                string="${{ steps.step1.outputs.ref }}",
                parts=parts,
            )
        ],
    )
    assert ref == should_be
