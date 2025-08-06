from abc import ABC, abstractmethod
from pathlib import Path

from validate_actions.globals.cli_config import CLIConfig
from validate_actions.globals.fixer import BaseFixer, NoFixer
from validate_actions.globals.validation_result import ValidationResult
from validate_actions.globals.web_fetcher import WebFetcher
from validate_actions.pipeline import Pipeline


class ValidationService(ABC):
    """Interface for validation services that process workflow files."""

    @abstractmethod
    def validate_file(self, file: Path, config: CLIConfig) -> ValidationResult:
        """Validate a single workflow file and return results."""
        pass


class StandardValidationService(ValidationService):
    """
    Standard validation service using the pipeline architecture.

    Creates a validation pipeline with the appropriate fixer and web fetcher
    based on the provided configuration.
    """

    def __init__(self, web_fetcher: WebFetcher):
        self.web_fetcher = web_fetcher

    def validate_file(self, file: Path, config: CLIConfig) -> ValidationResult:
        """Validate a single workflow file and return results."""
        fixer = BaseFixer(file) if config.fix else NoFixer()
        pipeline = Pipeline(self.web_fetcher, fixer)

        problems = pipeline.process(file)
        problems.sort()

        # Filter out warnings if quiet mode is enabled
        if config.no_warnings:
            problems = self._filter_warnings(problems)

        return ValidationResult(
            file=file,
            problems=problems,
            max_level=problems.max_level,
            error_count=problems.n_error,
            warning_count=problems.n_warning,
        )

    def _filter_warnings(self, problems):
        """Filter out warning-level problems and recalculate stats."""
        from validate_actions.globals.problems import Problems, ProblemLevel
        
        filtered = Problems()
        for problem in problems.problems:
            if problem.level != ProblemLevel.WAR:
                filtered.append(problem)
        
        return filtered
