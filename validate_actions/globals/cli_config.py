from dataclasses import dataclass
from typing import Optional


@dataclass
class CLIConfig:
    """
    Configuration for CLI operations.

    Attributes:
        fix: Whether to automatically fix detected problems
        workflow_file: Path to specific workflow file, or None to validate all
        github_token: GitHub token for API access, or None for no authentication
    """

    fix: bool
    workflow_file: Optional[str] = None
    github_token: Optional[str] = None
