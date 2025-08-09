"""End-to-end tests for auto-fix functionality."""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest


class TestFixMode:
    """End-to-end tests focused specifically on auto-fix functionality."""

    @pytest.fixture
    def temp_project(self):
        """Create a temporary project structure with .github/workflows directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_project_root = Path(temp_dir)
            workflows_dir = temp_project_root / ".github" / "workflows"
            workflows_dir.mkdir(parents=True)
            yield temp_project_root, workflows_dir

    def run_cli(self, cwd: Path, fix: bool = False) -> subprocess.CompletedProcess:
        """Run the validate-actions CLI command."""
        project_root = Path(__file__).parent.parent.parent

        cmd = ["validate-actions"]
        if fix:
            cmd.append("--fix")

        return subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=30,
            env={**os.environ, "PYTHONPATH": str(project_root)},
        )

    def test_fixable_workflow_gets_fixed(self, temp_project):
        """Test that fixable workflow issues are automatically corrected."""
        project_root, workflows_dir = temp_project

        # Copy fixable workflow to temp directory
        fixable_workflow = (
            Path(__file__).parent.parent / "fixtures" / "workflows" / "fixable_workflow.yml"
        )
        test_file = workflows_dir / "test.yml"
        shutil.copy(fixable_workflow, test_file)

        # Read original content
        original_content = test_file.read_text()

        result = self.run_cli(project_root, fix=True)

        # Should succeed after fixing
        assert result.returncode == 0

        # File should be modified
        fixed_content = test_file.read_text()
        assert fixed_content != original_content

        # Should contain fixed indicators
        assert "✓" in result.stdout

    def test_validation_after_fix_succeeds(self, temp_project):
        """Test that re-running validation after fix shows no errors."""
        project_root, workflows_dir = temp_project

        fixable_workflow = (
            Path(__file__).parent.parent / "fixtures" / "workflows" / "fixable_workflow.yml"
        )
        test_file = workflows_dir / "test.yml"
        shutil.copy(fixable_workflow, test_file)

        # First run with fix
        fix_result = self.run_cli(project_root, fix=True)
        assert fix_result.returncode == 0

        # Second run without fix should also succeed
        validation_result = self.run_cli(project_root, fix=False)
        assert validation_result.returncode == 0
        assert "✓" in validation_result.stdout

    def test_unfixable_errors_still_fail(self, temp_project):
        """Test that unfixable errors still cause failure even in fix mode."""
        project_root, workflows_dir = temp_project

        # Copy invalid workflow that cannot be auto-fixed
        invalid_workflow = (
            Path(__file__).parent.parent / "fixtures" / "workflows" / "invalid_workflow.yml"
        )
        shutil.copy(invalid_workflow, workflows_dir / "test.yml")

        result = self.run_cli(project_root, fix=True)

        # Should still fail because issues are not fixable
        assert result.returncode == 1
        assert "✗" in result.stdout

    def test_fix_mode_preserves_file_structure(self, temp_project):
        """Test that auto-fix preserves the overall structure of the workflow file."""
        project_root, workflows_dir = temp_project

        fixable_workflow = (
            Path(__file__).parent.parent / "fixtures" / "workflows" / "fixable_workflow.yml"
        )
        test_file = workflows_dir / "test.yml"
        shutil.copy(fixable_workflow, test_file)

        original_content = test_file.read_text()
        original_lines = original_content.splitlines()

        # Run fix
        self.run_cli(project_root, fix=True)

        fixed_content = test_file.read_text()
        fixed_lines = fixed_content.splitlines()

        # Basic structure should be preserved (similar line count)
        assert abs(len(fixed_lines) - len(original_lines)) < 5

        # Key elements should still be present
        assert "name:" in fixed_content
        assert "on:" in fixed_content
        assert "jobs:" in fixed_content

    def test_fix_mode_with_multiple_files(self, temp_project):
        """Test fix mode with multiple workflow files."""
        project_root, workflows_dir = temp_project

        fixable_workflow = (
            Path(__file__).parent.parent / "fixtures" / "workflows" / "fixable_workflow.yml"
        )

        # Create multiple copies
        test_file1 = workflows_dir / "workflow1.yml"
        test_file2 = workflows_dir / "workflow2.yml"
        shutil.copy(fixable_workflow, test_file1)
        shutil.copy(fixable_workflow, test_file2)

        original_content1 = test_file1.read_text()
        original_content2 = test_file2.read_text()

        result = self.run_cli(project_root, fix=True)

        # Should succeed
        assert result.returncode == 0

        # Both files should be modified
        fixed_content1 = test_file1.read_text()
        fixed_content2 = test_file2.read_text()
        assert fixed_content1 != original_content1
        assert fixed_content2 != original_content2

        # Output should mention both files
        assert "workflow1.yml" in result.stdout
        assert "workflow2.yml" in result.stdout
