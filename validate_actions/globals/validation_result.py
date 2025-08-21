"""Result of validating a single workflow file."""
from dataclasses import dataclass
from pathlib import Path

from validate_actions.globals.problems import ProblemLevel, Problems


@dataclass
class ValidationResult:
    """
    Result of validating a single workflow file.

    Attributes:
        file: Path to the validated workflow file
        problems: Collection of all problems found
        max_level: Highest severity level encountered
        error_count: Number of errors found
        warning_count: Number of warnings found
    """

    file: Path
    problems: Problems
    max_level: ProblemLevel
    error_count: int
    warning_count: int
