"""Holds CLI arguments configuration."""
import sys
from dataclasses import dataclass
from typing import Optional


@dataclass
class CLIConfig:
    """
    Configuration for CLI operations.

    Attributes:
        fix: Whether to automatically fix detected problems
        max_warnings: Maximum number of warnings before exiting with error code 1
        workflow_file: Path to specific workflow file, or None to validate all
        github_token: GitHub token for API access, or None for no authentication
        no_warnings: Whether to suppress warning-level problems in output
    """

    fix: bool
    max_warnings: int = sys.maxsize
    workflow_file: Optional[str] = None
    github_token: Optional[str] = None
    no_warnings: bool = False
