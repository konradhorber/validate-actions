from tests.conftest import parse_workflow_string
from validate_actions.domain_model import ast
from validate_actions.domain_model.primitives import Pos


class TestParser:
    def test_parse_str_to_ref(self):
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

    def test_flow_mapping_value_token_parsing(self):
        """Test flow mapping parsing handles ValueToken with ScalarToken, FlowMappingStartToken, and FlowSequenceStartToken."""
        # Test with scalar value
        workflow_string = """
on: push
jobs:
  test-job:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with: {ref: main}
"""
        workflow, problems = parse_workflow_string(workflow_string)
        with_value = workflow.jobs_["test-job"].steps_[0].exec.with_["ref"]
        assert with_value.string == "main"
        
        # Test with nested flow mapping
        workflow_string = """
on: push
jobs:
  test-job:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with: {config: {timeout: 30}}
"""
        workflow, problems = parse_workflow_string(workflow_string)
        config_value = workflow.jobs_["test-job"].steps_[0].exec.with_["config"]["timeout"]
        assert config_value == 30
        
        # Test with flow sequence
        workflow_string = """
on: push
jobs:
  test-job:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with: {files: [file1, file2]}
"""
        workflow, problems = parse_workflow_string(workflow_string)
        files_value = workflow.jobs_["test-job"].steps_[0].exec.with_["files"]
        assert len(files_value) == 2
        assert files_value[0].string == "file1"
        assert files_value[1].string == "file2"
