"""End-to-end tests using official GitHub Actions workflows.

These tests validate that all official GitHub workflow files in the fixtures
directory can be processed without errors, ensuring the tool works correctly
with real-world workflows.
"""

import subprocess
from pathlib import Path
from typing import List

import pytest


@pytest.fixture(scope="session")
def official_workflows_dir() -> Path:
    """Return the path to the official workflows directory."""
    workflows_dir = Path(__file__).parent.parent / "fixtures" / "workflows" / "official_workflows"
    if not workflows_dir.exists():
        pytest.skip(f"Official workflows directory not found at {workflows_dir}")
    return workflows_dir


@pytest.fixture(scope="session")
def workflow_files(official_workflows_dir: Path) -> List[Path]:
    """Get all workflow files from the official workflows directory."""
    workflow_files = []
    for pattern in ["*.yml", "*.yaml"]:
        workflow_files.extend(official_workflows_dir.rglob(pattern))
    return sorted(workflow_files)


def test_official_workflows_validate_without_errors(workflow_files: List[Path]):
    """
    Test that all official GitHub workflows validate without errors.

    This test runs the CLI tool on all workflow files individually
    with --quiet flag and ensures none fail with errors.
    Warnings are allowed.
    """
    if not workflow_files:
        pytest.skip("No workflow files found")

    failed_workflows = []

    for workflow_file in workflow_files:
        cmd = ["python", "-m", "validate_actions.main", "--quiet", str(workflow_file)]

        result = subprocess.run(
            cmd, cwd=Path(__file__).parent.parent.parent, capture_output=True, text=True
        )

        # Exit code 0 = no errors, exit code 2 = warnings only (acceptable)
        # Exit code 1 = errors (failure)
        if result.returncode == 1:
            rel_path = workflow_file.relative_to(workflow_file.parents[4])
            failed_workflows.append(
                {"file": str(rel_path), "stdout": result.stdout, "stderr": result.stderr}
            )
        elif result.returncode not in [0, 2]:
            rel_path = workflow_file.relative_to(workflow_file.parents[4])
            failed_workflows.append(
                {
                    "file": str(rel_path),
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "unexpected_exit_code": result.returncode,
                }
            )

    if failed_workflows:
        failure_msg = (
            f"\n{len(failed_workflows)} out of {len(workflow_files)} " f"workflows failed:\n\n"
        )
        for failure in failed_workflows:
            failure_msg += f"  {failure['file']}:\n"
            if "unexpected_exit_code" in failure:
                failure_msg += f"    Unexpected exit code: {failure['unexpected_exit_code']}\n"
            if failure["stdout"]:
                failure_msg += f"    STDOUT: {failure['stdout']}\n"
            if failure["stderr"]:
                failure_msg += f"    STDERR: {failure['stderr']}\n"
            failure_msg += "\n"

        pytest.fail(failure_msg)


def test_official_workflows_directory_not_empty(workflow_files: List[Path]):
    """
    Ensure we actually found workflow files to test.
    """
    assert len(workflow_files) > 0, "No workflow files found in official_workflows directory"
