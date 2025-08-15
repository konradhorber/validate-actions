import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from validate_actions import ProblemLevel, Problems
from validate_actions.cli import StandardCLI
from validate_actions.globals.cli_config import CLIConfig
from validate_actions.globals.validation_result import ValidationResult


class TestCLI:
    def test_run_directory_success(self):
        """Test _run_directory method with successful validation of workflow files."""
        # Create temp directory structure
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            github_dir = temp_path / ".github"
            workflows_dir = github_dir / "workflows"
            workflows_dir.mkdir(parents=True)

            # Create test workflow files
            workflow1 = workflows_dir / "test1.yml"
            workflow2 = workflows_dir / "test2.yaml"
            workflow1.write_text(
                "name: test1\non: push\njobs:\n  test:\n    runs-on: ubuntu-latest"
            )
            workflow2.write_text(
                "name: test2\non: pull_request\njobs:\n  test:\n    runs-on: ubuntu-latest"
            )

            # Create CLI instance with mocked dependencies
            config = CLIConfig(workflow_file=None, github_token="test", fix=False)
            formatter = Mock()
            aggregator = Mock()
            aggregator.get_exit_code.return_value = 0

            # Create mock validation results
            problems = Problems()
            result1 = ValidationResult(workflow1, problems, 0, 0, 0)
            result2 = ValidationResult(workflow2, problems, 0, 0, 0)

            cli = StandardCLI(config, formatter, aggregator)

            # Mock the directory finding and validation method to return our temp directory
            with patch.object(cli, "_find_workflows_directory", return_value=temp_path):
                with patch.object(cli, "_validate_file_with_pipeline", side_effect=[result1, result2]):
                    with patch("builtins.print"):  # Suppress progress output
                        exit_code = cli._run_directory()

            # Assertions
            assert exit_code == 0
            assert aggregator.add_result.call_count == 2
            aggregator.add_result.assert_any_call(result1)
            aggregator.add_result.assert_any_call(result2)

    def test_run(self):
        workflow_string = """name: test
on:
  push:
    branches: [ $default-branch ]
  pullrequest:
    branches: [ $default-branch ]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Notify Slack
        uses: 8398a7/action-slack
        with:
          unknown_input: 'test'
      - name: Notify Slack
        uses: 8398a7/action-slack@v3
        with:
          status: 'test'
"""
        with tempfile.NamedTemporaryFile(suffix=".yml", mode="w+", delete=False) as temp_file:
            temp_file.write(workflow_string)
            temp_file_path = Path(temp_file.name)

        try:
            from validate_actions.globals.fixer import NoFixer
            from validate_actions.globals.web_fetcher import DefaultWebFetcher
            from validate_actions.pipeline import DefaultPipeline

            web_fetcher = DefaultWebFetcher(github_token=os.getenv("GH_TOKEN"))
            pipeline = DefaultPipeline(temp_file_path, web_fetcher, NoFixer())
            problems = pipeline.process()
        finally:
            temp_file_path.unlink(missing_ok=True)

        problems.sort()
        problems_list = problems.problems

        assert len(problems_list) == 4
        rule_event = "events-syntax-error"
        rule_input = "jobs-steps-uses"
        assert problems_list[0].rule == rule_event
        assert problems_list[1].rule == rule_input
        assert problems_list[1].level == ProblemLevel.WAR
        assert problems_list[2].rule == rule_input
        assert problems_list[3].rule == rule_input
