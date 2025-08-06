from abc import ABC, abstractmethod
from typing import List

from validate_actions.globals.problems import ProblemLevel
from validate_actions.globals.validation_result import ValidationResult


class ResultAggregator(ABC):
    """Interface for aggregating validation results across multiple files."""

    @abstractmethod
    def add_result(self, result: ValidationResult) -> None:
        """Add a validation result to the aggregation."""
        pass

    @abstractmethod
    def get_total_errors(self) -> int:
        """Get total number of errors across all files."""
        pass

    @abstractmethod
    def get_total_warnings(self) -> int:
        """Get total number of warnings across all files."""
        pass

    @abstractmethod
    def get_max_level(self) -> ProblemLevel:
        """Get the highest problem level encountered."""
        pass

    @abstractmethod
    def get_exit_code(self) -> int:
        """Get appropriate exit code based on results."""
        pass

    @abstractmethod
    def get_results(self) -> List[ValidationResult]:
        """Get all validation results."""
        pass


class StandardResultAggregator(ResultAggregator):
    """
    Standard implementation of result aggregation.

    Tracks total errors, warnings, and determines appropriate exit codes.
    Exit codes: 0=success, 1=errors present, 2=warnings only.
    """

    def __init__(self) -> None:
        self._results: List[ValidationResult] = []
        self._total_errors = 0
        self._total_warnings = 0
        self._max_level = ProblemLevel.NON

    def add_result(self, result: ValidationResult) -> None:
        """Add a validation result and update aggregated stats."""
        self._results.append(result)
        self._total_errors += result.error_count
        self._total_warnings += result.warning_count
        self._max_level = ProblemLevel(max(self._max_level.value, result.max_level.value))

    def get_total_errors(self) -> int:
        """Get total errors across all files."""
        return self._total_errors

    def get_total_warnings(self) -> int:
        """Get total warnings across all files."""
        return self._total_warnings

    def get_max_level(self) -> ProblemLevel:
        """Get highest problem level encountered."""
        return self._max_level

    def get_exit_code(self) -> int:
        """Get exit code based on problem levels."""
        match self._max_level:
            case ProblemLevel.NON:
                return 0
            case ProblemLevel.WAR:
                return 2
            case ProblemLevel.ERR:
                return 1
            case _:
                raise ValueError(f"Invalid problem level: {self._max_level}")

    def get_results(self) -> List[ValidationResult]:
        """Get all validation results."""
        return self._results.copy()
