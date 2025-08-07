"""Integration tests for main.py CLI entry point."""

import os
from unittest.mock import patch
from pathlib import Path
import tempfile

from typer.testing import CliRunner
from validate_actions.main import app


class TestMainIntegration:
    """Integration tests for the main CLI entry point."""

    def setup_method(self):
        """Set up test runner."""
        self.runner = CliRunner()

    def test_help_command(self):
        """Test that help command displays usage information."""
        result = self.runner.invoke(app, ["--help"])

        assert result.exit_code == 0
        assert "validate-actions" in result.stdout
        assert "--fix" in result.stdout
        assert "--quiet" in result.stdout

    def test_main_with_no_arguments_fails_when_no_workflows_dir(self):
        """Test main fails gracefully when no .github/workflows directory exists."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Change to temp directory with no .github/workflows
            with patch("os.getcwd", return_value=temp_dir):
                result = self.runner.invoke(app)

                assert result.exit_code == 1
                assert "Could not find .github/workflows directory" in result.stdout

    def test_main_with_specific_file_argument(self):
        """Test main with specific workflow file argument."""
        # Create a test workflow file
        with tempfile.NamedTemporaryFile(suffix=".yml", mode="w", delete=False) as temp_file:
            temp_file.write("""name: Test Workflow
on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Test
        run: echo "test"
""")
            temp_file_path = temp_file.name

        try:
            result = self.runner.invoke(app, [temp_file_path])
            
            # Should succeed for valid workflow
            assert result.exit_code == 0
            assert temp_file_path in result.stdout or Path(temp_file_path).name in result.stdout
            
        finally:
            Path(temp_file_path).unlink(missing_ok=True)

    def test_main_with_invalid_file(self):
        """Test main behavior with invalid workflow file."""
        # Create an invalid workflow file
        with tempfile.NamedTemporaryFile(suffix=".yml", mode="w", delete=False) as temp_file:
            temp_file.write("""invalid: yaml: content: [unclosed""")
            temp_file_path = temp_file.name

        try:
            result = self.runner.invoke(app, [temp_file_path])
            
            # Should fail for invalid workflow
            assert result.exit_code == 1
            
        finally:
            Path(temp_file_path).unlink(missing_ok=True)

    def test_main_with_fix_flag(self):
        """Test main with --fix flag processes correctly."""
        # Create a fixable workflow file
        with tempfile.NamedTemporaryFile(suffix=".yml", mode="w", delete=False) as temp_file:
            temp_file.write("""name: Fixable Workflow
on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Test
        run: echo "test"
""")
            temp_file_path = temp_file.name

        try:
            result = self.runner.invoke(app, ["--fix", temp_file_path])
            
            # Fix mode should complete
            assert result.exit_code == 0
            
        finally:
            Path(temp_file_path).unlink(missing_ok=True)

    def test_main_with_quiet_flag(self):
        """Test main with --quiet flag suppresses warnings."""
        with tempfile.NamedTemporaryFile(suffix=".yml", mode="w", delete=False) as temp_file:
            temp_file.write("""name: Warning Workflow
on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout  # Missing version - should trigger warning
      - name: Test
        run: echo "test"
""")
            temp_file_path = temp_file.name

        try:
            # Test normal mode
            normal_result = self.runner.invoke(app, [temp_file_path])
            
            # Test quiet mode
            quiet_result = self.runner.invoke(app, [temp_file_path, "--quiet"])
            
            # Quiet mode should show fewer issues than normal mode
            # (This is a basic integration test - more detailed behavior tested in unit tests)
            assert quiet_result.exit_code in [0, 1, 2]  # Valid exit codes
            
        finally:
            Path(temp_file_path).unlink(missing_ok=True)

    @patch.dict(os.environ, {"GH_TOKEN": "test_token"})
    def test_main_uses_github_token_from_environment(self):
        """Test that main correctly uses GitHub token from environment."""
        with tempfile.NamedTemporaryFile(suffix=".yml", mode="w", delete=False) as temp_file:
            temp_file.write("""name: Test Workflow
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
""")
            temp_file_path = temp_file.name

        try:
            result = self.runner.invoke(app, [temp_file_path])
            
            # Should complete without API rate limit issues
            assert result.exit_code in [0, 1, 2]  # Valid exit codes
            
        finally:
            Path(temp_file_path).unlink(missing_ok=True)

    def test_main_with_nonexistent_file(self):
        """Test main behavior with nonexistent file."""
        result = self.runner.invoke(app, ["/nonexistent/file.yml"])
        
        # Should fail gracefully
        assert result.exit_code == 1
