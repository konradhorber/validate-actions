"""Aggregates validation results for CLI output. Especially for multiple files."""
from abc import ABC, abstractmethod
from typing import List

from validate_actions.globals.cli_config import CLIConfig
from validate_actions.globals.problems import ProblemLevel
from validate_actions.globals.validation_result import ValidationResult


class ResultAggregator(ABC):
    """Abstract base class for aggregating validation results across multiple files."""

    def __init__(self, cli_config: CLIConfig) -> None:
        self._results: List[ValidationResult] = []
        self._total_errors = 0
        self._total_warnings = 0
        self._max_level = ProblemLevel.NON

    def get_total_errors(self) -> int:
        """Get total errors across all files."""
        return self._total_errors

    def get_total_warnings(self) -> int:
        """Get total warnings across all files."""
        return self._total_warnings

    def get_max_level(self) -> ProblemLevel:
        """Get highest problem level encountered."""
        return self._max_level

    def get_results(self) -> List[ValidationResult]:
        """Get all validation results."""
        return self._results.copy()

    @abstractmethod
    def add_result(self, result: ValidationResult) -> None:
        """Add a validation result and update aggregated stats."""
        pass

    @abstractmethod
    def get_exit_code(self) -> int:
        """Get appropriate exit code based on results."""
        pass


class StandardResultAggregator(ResultAggregator):
    """Standard implementation with exit code 0 for any warnings and 1 for errors."""

    def add_result(self, result: ValidationResult) -> None:
        """Add a validation result and update aggregated stats."""
        self._results.append(result)
        self._total_errors += result.error_count
        self._total_warnings += result.warning_count
        self._max_level = ProblemLevel(max(self._max_level.value, result.max_level.value))

    def get_exit_code(self) -> int:
        """Get exit code based on problem levels."""
        match self._max_level:
            case ProblemLevel.NON:
                return 0
            case ProblemLevel.WAR:
                return 0
            case ProblemLevel.ERR:
                return 1
            case _:
                raise ValueError(f"Invalid problem level: {self._max_level}")


class MaxWarningsResultAggregator(ResultAggregator):
    """Result aggregator that enforces a maximum number of warnings."""

    def __init__(self, cli_config: CLIConfig) -> None:
        super().__init__(cli_config)
        self._max_warnings = cli_config.max_warnings

    def add_result(self, result: ValidationResult) -> None:
        """Add a validation result and update aggregated stats."""
        self._results.append(result)
        self._total_errors += result.error_count
        self._total_warnings += result.warning_count
        self._max_level = ProblemLevel(max(self._max_level.value, result.max_level.value))
        if self._total_warnings > self._max_warnings:
            self._max_level = ProblemLevel.ERR

    def get_exit_code(self) -> int:
        """Get exit code based on problem levels and max warnings limit."""
        match self._max_level:
            case ProblemLevel.NON:
                return 0
            case ProblemLevel.WAR:
                return 1 if self._total_warnings > self._max_warnings else 0
            case ProblemLevel.ERR:
                return 1
            case _:
                raise ValueError(f"Invalid problem level: {self._max_level}")
