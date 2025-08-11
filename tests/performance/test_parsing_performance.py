"""Performance tests for parsing official GitHub Actions workflows.

These tests measure parsing performance to ensure the tool remains fast
when processing real-world workflow files.
"""

import subprocess
import time
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


def test_parsing_performance_under_1_second_per_file(workflow_files: List[Path]):
    """
    Test that parsing performance averages under 1 second per workflow file.
    
    This test ensures the validation tool maintains reasonable performance
    when processing large numbers of workflow files.
    """
    if not workflow_files:
        pytest.skip("No workflow files found")
    
    start_time = time.time()
    processed_count = 0
    failed_count = 0
    
    for workflow_file in workflow_files:
        file_start = time.time()
        rel_path = workflow_file.relative_to(workflow_file.parents[4])
        
        cmd = ["python", "-m", "validate_actions.main", "--quiet", str(workflow_file)]
        
        result = subprocess.run(
            cmd,
            cwd=Path(__file__).parent.parent.parent,
            capture_output=True,
            text=True
        )
        
        file_end = time.time()
        file_duration = file_end - file_start
        
        processed_count += 1
        if result.returncode == 1:
            failed_count += 1
        
        # Fail immediately for files taking longer than 2 seconds
        if file_duration > 2.0:
            pytest.fail(
                f"File {rel_path} took {file_duration:.3f}s to process (exceeds 2.0s limit)\n"
                f"This indicates a performance regression in the validation logic."
            )
    
    end_time = time.time()
    total_duration = end_time - start_time
    average_duration = total_duration / len(workflow_files)
    
    # Assert average performance is under 1 second per file
    assert average_duration < 1.0, (
        f"Average parsing time {average_duration:.3f}s exceeds 1.0s limit\n"
        f"Processed {processed_count} files in {total_duration:.2f}s"
    )

