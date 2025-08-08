import os
import tempfile
from pathlib import Path

from validate_actions.cli_components.validation_service import StandardValidationService
from validate_actions.globals.cli_config import CLIConfig
from validate_actions.globals.problems import ProblemLevel
from validate_actions.globals.web_fetcher import DefaultWebFetcher


class TestValidationService:
    def test_quiet_mode_filters_warnings(self):
        """Test that quiet mode filters out warning-level problems."""
        # Create a workflow with warnings (missing action versions)
        workflow_string = """name: Warning Workflow
on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout  # Missing version - should trigger warning
      - name: Setup Node
        uses: actions/setup-node  # Missing version - should trigger warning
        with:
          node-version: '18'
"""
        with tempfile.NamedTemporaryFile(suffix=".yml", mode="w+", delete=False) as temp_file:
            temp_file.write(workflow_string)
            temp_file_path = Path(temp_file.name)

        try:
            web_fetcher = DefaultWebFetcher(github_token=os.getenv("GH_TOKEN"))
            validation_service = StandardValidationService(web_fetcher)

            # Test normal mode (warnings should be included)
            normal_config = CLIConfig(fix=False, no_warnings=False)
            normal_result = validation_service.validate_file(temp_file_path, normal_config)

            # Test quiet mode (warnings should be filtered out)
            quiet_config = CLIConfig(fix=False, no_warnings=True)
            quiet_result = validation_service.validate_file(temp_file_path, quiet_config)

        finally:
            temp_file_path.unlink(missing_ok=True)

        # Assertions for normal mode
        assert normal_result.warning_count == 2
        assert normal_result.error_count == 0
        assert normal_result.max_level == ProblemLevel.WAR
        assert len(normal_result.problems.problems) == 2

        # All problems in normal mode should be warnings
        for problem in normal_result.problems.problems:
            assert problem.level == ProblemLevel.WAR
            assert "actions/checkout" in problem.desc or "actions/setup-node" in problem.desc
            assert problem.rule == "jobs-steps-uses"

        # Assertions for quiet mode
        assert quiet_result.warning_count == 0
        assert quiet_result.error_count == 0
        assert quiet_result.max_level == ProblemLevel.NON
        assert len(quiet_result.problems.problems) == 0

    def test_quiet_mode_preserves_errors(self):
        """Test that quiet mode preserves error-level problems while filtering warnings."""
        # Create a workflow with both errors and warnings
        workflow_string = """name: Mixed Problems Workflow
on:
  push:
    branches: [main]
  pullrequest:  # Typo: should be pull_request - triggers error
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout  # Missing version - should trigger warning
      - name: Context Error
        run: echo "${{ github.invalid_context }}"  # Invalid context - triggers error
"""

        with tempfile.NamedTemporaryFile(suffix=".yml", mode="w+", delete=False) as temp_file:
            temp_file.write(workflow_string)
            temp_file_path = Path(temp_file.name)

        try:
            web_fetcher = DefaultWebFetcher(github_token=os.getenv("GH_TOKEN"))
            validation_service = StandardValidationService(web_fetcher)

            # Test normal mode (both errors and warnings should be included)
            normal_config = CLIConfig(fix=False, no_warnings=False)
            normal_result = validation_service.validate_file(temp_file_path, normal_config)

            # Test quiet mode (only errors should be preserved)
            quiet_config = CLIConfig(fix=False, no_warnings=True)
            quiet_result = validation_service.validate_file(temp_file_path, quiet_config)

        finally:
            temp_file_path.unlink(missing_ok=True)

        # Assertions for normal mode - should have both warnings and errors
        assert normal_result.warning_count > 0  # At least one warning
        assert normal_result.error_count > 0  # At least one error
        assert normal_result.max_level == ProblemLevel.ERR

        # Should have problems of different levels
        warning_problems = [
            p for p in normal_result.problems.problems if p.level == ProblemLevel.WAR
        ]
        error_problems = [
            p for p in normal_result.problems.problems if p.level == ProblemLevel.ERR
        ]
        assert len(warning_problems) > 0
        assert len(error_problems) > 0

        # Assertions for quiet mode - should only have errors
        assert quiet_result.warning_count == 0  # Warnings filtered out
        assert quiet_result.error_count > 0  # Errors preserved
        assert quiet_result.max_level == ProblemLevel.ERR

        # All remaining problems should be errors
        for problem in quiet_result.problems.problems:
            assert problem.level == ProblemLevel.ERR

        # Number of problems should be reduced (warnings filtered out)
        assert len(quiet_result.problems.problems) < len(normal_result.problems.problems)
        assert len(quiet_result.problems.problems) == len(error_problems)

    def test_quiet_mode_no_effect_on_error_only_workflow(self):
        """Test that quiet mode has no effect when there are only errors."""
        # Create a workflow with only errors
        workflow_string = """name: Error Only Workflow
on:
  pullrequest:  # Typo: should be pull_request - triggers error
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - name: Context Error
        run: echo "${{ github.invalid_context }}"  # Invalid context - triggers error
"""

        with tempfile.NamedTemporaryFile(suffix=".yml", mode="w+", delete=False) as temp_file:
            temp_file.write(workflow_string)
            temp_file_path = Path(temp_file.name)

        try:
            web_fetcher = DefaultWebFetcher(github_token=os.getenv("GH_TOKEN"))
            validation_service = StandardValidationService(web_fetcher)

            # Test both modes
            normal_config = CLIConfig(fix=False, no_warnings=False)
            normal_result = validation_service.validate_file(temp_file_path, normal_config)

            quiet_config = CLIConfig(fix=False, no_warnings=True)
            quiet_result = validation_service.validate_file(temp_file_path, quiet_config)

        finally:
            temp_file_path.unlink(missing_ok=True)

        # Both results should be identical since there are no warnings to filter
        assert normal_result.warning_count == quiet_result.warning_count == 0
        assert normal_result.error_count == quiet_result.error_count
        assert normal_result.max_level == quiet_result.max_level == ProblemLevel.ERR
        assert len(normal_result.problems.problems) == len(quiet_result.problems.problems)
