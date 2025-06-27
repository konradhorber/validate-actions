"""End-to-end tests for validate-actions CLI tool."""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest


class TestE2E:
    """End-to-end tests that run the actual CLI command."""

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
        project_root = Path(__file__).parent.parent

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

    def test_valid_workflow_passes(self, temp_project):
        """Test that a valid workflow file passes validation."""
        project_root, workflows_dir = temp_project

        # Copy valid workflow to temp directory
        valid_workflow = Path(__file__).parent / "resources" / "valid_workflow.yml"
        shutil.copy(valid_workflow, workflows_dir / "test.yml")

        result = self.run_cli(project_root)

        assert result.returncode == 0
        assert "✓" in result.stdout  # Success indicator

    def test_invalid_workflow_fails_validation(self, temp_project):
        """Test that an invalid workflow file fails validation."""
        project_root, workflows_dir = temp_project

        # Copy invalid workflow to temp directory
        invalid_workflow = Path(__file__).parent / "resources" / "invalid_workflow.yml"
        shutil.copy(invalid_workflow, workflows_dir / "test.yml")

        result = self.run_cli(project_root)

        assert result.returncode == 1
        assert "✗" in result.stdout  # Error indicator

    def test_fixable_workflow_validation_mode(self, temp_project):
        """Test fixable workflow in validation-only mode (should report errors)."""
        project_root, workflows_dir = temp_project

        # Copy fixable workflow to temp directory
        fixable_workflow = Path(__file__).parent / "resources" / "fixable_workflow.yml"
        shutil.copy(fixable_workflow, workflows_dir / "test.yml")

        result = self.run_cli(project_root, fix=False)

        assert result.returncode == 1 or result.returncode == 2  # Should return error or warning
        assert "⚠" in result.stdout or "✗" in result.stdout  # Warning or error indicator

    def test_fixable_workflow_fix_mode(self, temp_project):
        """Test fixable workflow in auto-fix mode (should fix issues)."""
        project_root, workflows_dir = temp_project

        # Copy fixable workflow to temp directory
        fixable_workflow = Path(__file__).parent / "resources" / "fixable_workflow.yml"
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

    def test_multiple_workflow_files(self, temp_project):
        """Test validation with multiple workflow files."""
        project_root, workflows_dir = temp_project

        # Copy multiple workflow files
        valid_workflow = Path(__file__).parent / "resources" / "valid_workflow.yml"
        invalid_workflow = Path(__file__).parent / "resources" / "invalid_workflow.yml"

        shutil.copy(valid_workflow, workflows_dir / "valid.yml")
        shutil.copy(invalid_workflow, workflows_dir / "invalid.yml")

        result = self.run_cli(project_root)

        assert result.returncode == 1  # Should fail due to invalid workflow
        assert "valid.yml" in result.stdout
        assert "invalid.yml" in result.stdout

    def test_no_workflows_directory(self):
        """Test behavior when no .github/workflows directory exists."""
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.run_cli(Path(temp_dir))

            assert result.returncode == 1
            assert "Could not find .github/workflows directory" in result.stdout

    def test_empty_workflows_directory(self, temp_project):
        """Test behavior with empty workflows directory."""
        project_root, _ = temp_project

        result = self.run_cli(project_root)

        # Should fail with no files to validate
        assert result.returncode == 1

    def test_yaml_and_yml_extensions(self, temp_project):
        """Test that both .yml and .yaml extensions are processed."""
        project_root, workflows_dir = temp_project

        valid_workflow = Path(__file__).parent / "resources" / "valid_workflow.yml"

        # Create files with both extensions
        shutil.copy(valid_workflow, workflows_dir / "test1.yml")
        shutil.copy(valid_workflow, workflows_dir / "test2.yaml")

        result = self.run_cli(project_root)

        assert result.returncode == 0
        assert "test1.yml" in result.stdout
        assert "test2.yaml" in result.stdout

    def test_cli_help_option(self):
        """Test that CLI help option works."""
        result = subprocess.run(
            ["poetry", "run", "validate-actions", "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 0
        assert "fix" in result.stdout.lower()
        assert "automatically" in result.stdout.lower()

    def test_exit_codes(self, temp_project):
        """Test that appropriate exit codes are returned."""
        project_root, workflows_dir = temp_project

        # Test success case (exit code 0)
        valid_workflow = Path(__file__).parent / "resources" / "valid_workflow.yml"
        shutil.copy(valid_workflow, workflows_dir / "valid.yml")

        result = self.run_cli(project_root)
        assert result.returncode == 0

        # Test failure case (exit code 1)
        invalid_workflow = Path(__file__).parent / "resources" / "invalid_workflow.yml"
        shutil.copy(invalid_workflow, workflows_dir / "invalid.yml")

        result = self.run_cli(project_root)
        assert result.returncode == 1

        # Test warning case (exit code 2)
        warning_workflow = Path(__file__).parent / "resources" / "warning_workflow.yml"
        shutil.copy(warning_workflow, workflows_dir / "warning.yml")

        # Remove other files to test only warnings
        for f in workflows_dir.glob("*.yml"):
            if f.name != "warning.yml":
                f.unlink()

        result = self.run_cli(project_root)
        assert result.returncode == 2
        assert "⚠" in result.stdout  # Should show warning indicator

    def test_demo_needs_validation_workflow(self, temp_project):
        """Test demo workflow with invalid job needs references."""
        project_root, workflows_dir = temp_project

        # Copy the needs validation demo workflow
        demo_workflow = Path(__file__).parent / "resources" / "needs_validation_workflow.yml"
        shutil.copy(demo_workflow, workflows_dir / "needs-validation.yml")

        result = self.run_cli(project_root)

        # Should fail due to invalid needs reference
        assert result.returncode == 1
        assert "needs-validation.yml" in result.stdout
        assert "✗" in result.stdout  # Error indicator
        
        # Should detect missing job reference
        assert "missing-job" in result.stdout or "does not exist" in result.stdout.lower()
        
        # Should detect invalid needs context
        output_lower = result.stdout.lower()
        assert "needs" in output_lower and ("context" in output_lower or "reference" in output_lower)

    def test_demo_circular_dependencies_workflow(self, temp_project):
        """Test demo workflow with circular job dependencies."""
        project_root, workflows_dir = temp_project

        # Copy the circular dependencies demo workflow
        demo_workflow = Path(__file__).parent / "resources" / "circular_dependencies_workflow.yml"
        shutil.copy(demo_workflow, workflows_dir / "circular-deps.yml")

        result = self.run_cli(project_root)

        # Should fail due to circular dependencies
        assert result.returncode == 1
        assert "circular-deps.yml" in result.stdout
        assert "✗" in result.stdout  # Error indicator
        
        # Should detect circular dependency
        output_lower = result.stdout.lower()
        assert "circular" in output_lower or "cycle" in output_lower or "dependency" in output_lower

    def test_demo_outdated_actions_workflow(self, temp_project):
        """Test demo workflow with outdated action versions."""
        project_root, workflows_dir = temp_project

        # Copy the outdated actions demo workflow
        demo_workflow = Path(__file__).parent / "resources" / "outdated_actions_workflow.yml"
        shutil.copy(demo_workflow, workflows_dir / "outdated-actions.yml")

        result = self.run_cli(project_root)

        # Should fail or warn due to outdated actions
        assert result.returncode in [1, 2]  # Error or warning
        assert "outdated-actions.yml" in result.stdout
        assert ("✗" in result.stdout or "⚠" in result.stdout)  # Error or warning indicator
        
        # Should detect outdated versions
        output_lower = result.stdout.lower()
        assert ("outdated" in output_lower or "v3" in result.stdout or "v4" in result.stdout or 
                "sha" in output_lower or "version" in output_lower)
