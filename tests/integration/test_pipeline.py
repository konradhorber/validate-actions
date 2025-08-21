"""Tests for pipeline functionality."""

import tempfile
from pathlib import Path

from validate_actions.pipeline_stages.parser import PyYAMLParser
from validate_actions.pipeline_stages.builder import DefaultBuilder
from validate_actions.pipeline_stages.validator import ExtensibleValidator
from validate_actions.globals.fixer import NoFixer
from validate_actions.globals.problems import Problems
from validate_actions.pipeline import Pipeline


class SimplePipeline(Pipeline):
    """Pipeline with only parser, builder, and validator stages."""

    def __init__(self, file: Path):
        fixer = NoFixer()
        super().__init__(file, fixer)

        self.parser = PyYAMLParser(self.problems)
        self.builder = DefaultBuilder(self.problems)
        self.validator = ExtensibleValidator(self.problems, self.fixer)

    def process(self) -> Problems:
        dict_result = self.parser.process(self.file)
        workflow = self.builder.process(dict_result)
        problems = self.validator.process(workflow)
        return problems


class TestSimplePipeline:
    """Test the simplified pipeline (parser + builder + validator only)."""

    def test_simple_pipeline_healthy_workflow(self):
        """Test that a healthy workflow processes without errors."""
        # Create a simple, valid workflow
        workflow_content = """
name: Test Workflow
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4
      - name: Setup Node
        uses: actions/setup-node@v4
        with:
          node-version: '18'
      - name: Run tests
        run: npm test
"""

        # Write workflow to temporary file
        with tempfile.NamedTemporaryFile(suffix=".yml", mode="w+", delete=False) as temp_file:
            temp_file.write(workflow_content)
            temp_file_path = Path(temp_file.name)

        try:
            # Process with simple pipeline
            pipeline = SimplePipeline(temp_file_path)
            problems = pipeline.process()

            # Should not have any problems
            assert problems is not None
            assert len(problems.problems) == 0

        finally:
            # Cleanup
            temp_file_path.unlink(missing_ok=True)

    def test_simple_pipeline_with_context_expressions(self):
        """Test pipeline handles GitHub context expressions correctly."""
        workflow_content = """
name: Context Test
on: push

env:
  GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}

jobs:
  build:
    runs-on: ubuntu-latest
    if: github.event_name == 'push'
    steps:
      - name: Checkout
        uses: actions/checkout@v4
      - name: Use context
        run: echo "Repository is ${{ github.repository }}"
        env:
          BRANCH: ${{ github.ref_name }}
"""

        with tempfile.NamedTemporaryFile(suffix=".yml", mode="w+", delete=False) as temp_file:
            temp_file.write(workflow_content)
            temp_file_path = Path(temp_file.name)

        try:
            pipeline = SimplePipeline(temp_file_path)
            problems = pipeline.process()

            # Should process without critical errors
            assert problems is not None
            critical_errors = [p for p in problems.problems if p.level.name == "ERR"]
            assert len(critical_errors) == 0

        finally:
            temp_file_path.unlink(missing_ok=True)
