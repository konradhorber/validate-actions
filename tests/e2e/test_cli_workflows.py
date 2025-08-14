"""End-to-end tests for validate-actions CLI tool."""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import List

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

    def run_cli(self, cwd: Path, fix: bool = False, extra_args: List[str] = None) -> subprocess.CompletedProcess:
        """Run the validate-actions CLI command."""
        project_root = Path(__file__).parent.parent.parent

        cmd = ["validate-actions"]
        if fix:
            cmd.append("--fix")
        if extra_args:
            cmd.extend(extra_args)

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
        valid_workflow = (
            Path(__file__).parent.parent / "fixtures" / "workflows" / "valid_workflow.yml"
        )
        shutil.copy(valid_workflow, workflows_dir / "test.yml")

        result = self.run_cli(project_root)

        assert result.returncode == 0
        assert "✓" in result.stdout  # Success indicator

    def test_invalid_workflow_fails_validation(self, temp_project):
        """Test that an invalid workflow file fails validation."""
        project_root, workflows_dir = temp_project

        # Copy invalid workflow to temp directory
        invalid_workflow = (
            Path(__file__).parent.parent / "fixtures" / "workflows" / "invalid_workflow.yml"
        )
        shutil.copy(invalid_workflow, workflows_dir / "test.yml")

        result = self.run_cli(project_root)

        assert result.returncode == 1
        assert "error" in result.stdout  # Error indicator

    def test_multiple_workflow_files(self, temp_project):
        """Test validation with multiple workflow files."""
        project_root, workflows_dir = temp_project

        # Copy multiple workflow files
        valid_workflow = (
            Path(__file__).parent.parent / "fixtures" / "workflows" / "valid_workflow.yml"
        )
        invalid_workflow = (
            Path(__file__).parent.parent / "fixtures" / "workflows" / "invalid_workflow.yml"
        )

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

        valid_workflow = (
            Path(__file__).parent.parent / "fixtures" / "workflows" / "valid_workflow.yml"
        )

        # Create files with both extensions
        shutil.copy(valid_workflow, workflows_dir / "test1.yml")
        shutil.copy(valid_workflow, workflows_dir / "test2.yaml")

        result = self.run_cli(project_root)

        assert result.returncode == 0
        assert "test1.yml" in result.stdout
        assert "test2.yaml" in result.stdout

    def test_cli_help_option(self):
        """Test that CLI help option works."""
        project_root = Path(__file__).parent.parent.parent
        result = subprocess.run(
            ["validate-actions", "--help"],
            capture_output=True,
            text=True,
            timeout=10,
            env={**os.environ, "PYTHONPATH": str(project_root)},
        )

        assert result.returncode == 0
        assert "fix" in result.stdout.lower()
        assert "automatically" in result.stdout.lower()

    def test_exit_codes(self, temp_project):
        """Test that appropriate exit codes are returned."""
        project_root, workflows_dir = temp_project

        # Test success case (exit code 0)
        valid_workflow = (
            Path(__file__).parent.parent / "fixtures" / "workflows" / "valid_workflow.yml"
        )
        shutil.copy(valid_workflow, workflows_dir / "valid.yml")

        result = self.run_cli(project_root)
        assert result.returncode == 0

        # Test failure case (exit code 1)
        invalid_workflow = (
            Path(__file__).parent.parent / "fixtures" / "workflows" / "invalid_workflow.yml"
        )
        shutil.copy(invalid_workflow, workflows_dir / "invalid.yml")

        result = self.run_cli(project_root)
        assert result.returncode == 1

        # Test warning case (exit code 0)
        warning_workflow = (
            Path(__file__).parent.parent / "fixtures" / "workflows" / "warning_workflow.yml"
        )
        shutil.copy(warning_workflow, workflows_dir / "warning.yml")

        # Remove other files to test only warnings
        for f in workflows_dir.glob("*.yml"):
            if f.name != "warning.yml":
                f.unlink()

        result = self.run_cli(project_root)
        assert result.returncode == 0
        assert "⚠" in result.stdout  # Should show warning indicator

    def test_demo_needs_validation_workflow(self, temp_project):
        """Test demo workflow with invalid job needs references."""
        project_root, workflows_dir = temp_project

        # Copy the needs validation demo workflow
        demo_workflow = (
            Path(__file__).parent.parent
            / "fixtures"
            / "workflows"
            / "needs_validation_workflow.yml"
        )
        shutil.copy(demo_workflow, workflows_dir / "needs-validation.yml")

        result = self.run_cli(project_root)

        # Should fail due to invalid needs reference
        assert result.returncode == 1
        assert "needs-validation.yml" in result.stdout
        assert "error" in result.stdout  # Error indicator

        # Should detect missing job reference
        assert "missing-job" in result.stdout or "does not exist" in result.stdout.lower()

        # Should detect invalid needs context
        output_lower = result.stdout.lower()
        assert "needs" in output_lower and (
            "context" in output_lower or "reference" in output_lower
        )

    def test_demo_circular_dependencies_workflow(self, temp_project):
        """Test demo workflow with circular job dependencies."""
        project_root, workflows_dir = temp_project

        # Copy the circular dependencies demo workflow
        demo_workflow = (
            Path(__file__).parent.parent
            / "fixtures"
            / "workflows"
            / "circular_dependencies_workflow.yml"
        )
        shutil.copy(demo_workflow, workflows_dir / "circular-deps.yml")

        result = self.run_cli(project_root)

        # Should fail due to circular dependencies
        assert result.returncode == 1
        assert "circular-deps.yml" in result.stdout
        assert "error" in result.stdout  # Error indicator

        # Should detect circular dependency
        output_lower = result.stdout.lower()
        assert (
            "circular" in output_lower or "cycle" in output_lower or "dependency" in output_lower
        )

    def test_demo_outdated_actions_workflow(self, temp_project):
        """Test demo workflow with outdated action versions."""
        project_root, workflows_dir = temp_project

        # Copy the outdated actions demo workflow
        demo_workflow = (
            Path(__file__).parent.parent
            / "fixtures"
            / "workflows"
            / "outdated_actions_workflow.yml"
        )
        shutil.copy(demo_workflow, workflows_dir / "outdated-actions.yml")

        result = self.run_cli(project_root)

        # Should fail or warn due to outdated actions
        assert result.returncode == 0  # warning
        assert "outdated-actions.yml" in result.stdout
        assert "error" in result.stdout or "warning" in result.stdout  # Error or warning indicator

        # Should detect outdated versions
        output_lower = result.stdout.lower()
        assert (
            "outdated" in output_lower
            or "v3" in result.stdout
            or "v4" in result.stdout
            or "sha" in output_lower
            or "version" in output_lower
        )

    def test_max_warnings_option(self, temp_project):
        """Test --max-warnings CLI option behavior."""
        project_root, workflows_dir = temp_project

        # Create a workflow file that generates warnings for missing action versions
        warning_workflow_content = """
name: Warning Test
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout without version
        uses: actions/checkout
      - name: Setup Node without version
        uses: actions/setup-node
        with:
          node-version: '18'
      - name: Cache without version
        uses: actions/cache
        with:
          path: node_modules
          key: cache-key
"""
        
        warning_workflow_path = workflows_dir / "warnings.yml"
        warning_workflow_path.write_text(warning_workflow_content.strip())

        # Test 1: No max-warnings limit (should exit with code 0 for warnings)
        result = self.run_cli(project_root)
        assert result.returncode == 0  # Standard behavior: warnings return 0
        # Should show either ⚠ or at least mention warnings in the output
        output_lower = result.stdout.lower()
        assert "⚠" in result.stdout or "warning" in output_lower

        # Test 2: max-warnings=5 (above actual warning count, should pass)
        result = self.run_cli(project_root, extra_args=["--max-warnings", "5"])
        assert result.returncode == 0
        output_lower = result.stdout.lower()
        assert "⚠" in result.stdout or "warning" in output_lower

        # Test 3: max-warnings=3 (equal to warning count, should pass) 
        result = self.run_cli(project_root, extra_args=["--max-warnings", "3"])
        assert result.returncode == 0
        output_lower = result.stdout.lower()
        assert "⚠" in result.stdout or "warning" in output_lower

        # Test 4: max-warnings=2 (below warning count, should fail)
        result = self.run_cli(project_root, extra_args=["--max-warnings", "2"])
        assert result.returncode == 1  # Should exit with error code when warnings exceed limit
        output_lower = result.stdout.lower()
        assert "⚠" in result.stdout or "warning" in output_lower

        # Test 5: max-warnings=0 (no warnings allowed, should fail)
        result = self.run_cli(project_root, extra_args=["--max-warnings", "0"])  
        assert result.returncode == 1
        output_lower = result.stdout.lower()
        assert "⚠" in result.stdout or "warning" in output_lower
