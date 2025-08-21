"""CLI interface and standard implementation for validate-actions."""
import sys
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional

from rich.progress import Progress, SpinnerColumn, TextColumn

from validate_actions.cli_components.output_formatter import OutputFormatter, RichFormatter
from validate_actions.cli_components.result_aggregator import (
    MaxWarningsResultAggregator,
    ResultAggregator,
    StandardResultAggregator,
)
from validate_actions.globals.cli_config import CLIConfig
from validate_actions.globals.fixer import BaseFixer, NoFixer
from validate_actions.globals.validation_result import ValidationResult
from validate_actions.globals.web_fetcher import CachedWebFetcher
from validate_actions.pipeline import DefaultPipeline


class CLI(ABC):
    """Interface for CLI implementations."""

    @abstractmethod
    def run(self) -> int:
        """
        Run the CLI and return exit code.

        Returns:
            int: Exit code (0=success, 1=errors, 2=warnings only)
        """
        pass


class StandardCLI(CLI):
    """
    Standard CLI implementation with separated concerns.

    Coordinates validation using pluggable components:
    - OutputFormatter: handles display formatting
    - ResultAggregator: collects and summarizes results
    - Pipeline creation: creates pipelines for each file
    """

    def __init__(
        self,
        config: CLIConfig,
        formatter: Optional[OutputFormatter] = None,
        aggregator: Optional[ResultAggregator] = None,
    ):
        """
        Initialize CLI with configuration and optional component overrides.

        Args:
            config: CLI configuration (fix mode, workflow file, GitHub token)
            formatter: Output formatter (defaults to RichFormatter)
            aggregator: Result aggregator (defaults to StandardResultAggregator)
        """
        self.config = config
        self.formatter = formatter or RichFormatter()
        if config.max_warnings < sys.maxsize:
            aggregator = MaxWarningsResultAggregator(config)
        self.aggregator = aggregator or StandardResultAggregator(config)

        # Create web fetcher (reusable across files)
        self.web_fetcher = CachedWebFetcher(github_token=config.github_token)

    def run(self) -> int:
        """Main CLI execution method.

        Orchestrates the complete validation process, including file discovery,
        validation execution, result collection, and output formatting.

        Validates either a single workflow file (if specified in config) or
        discovers and validates all workflow files in the .github/workflows/
        directory.

        Returns:
            int: Exit code indicating validation results:
                - 0: Success (no errors)
                - 1: Errors found
                - 2: Warnings only (when not suppressed)

        Examples:
            Single file validation:
                cli = StandardCLI(config_with_file)
                exit_code = cli.run()

            Directory validation:
                cli = StandardCLI(config_without_file)
                exit_code = cli.run()
        """
        if self.config.workflow_file:
            return self._run_single_file(Path(self.config.workflow_file))
        else:
            return self._run_directory()

    def _run_single_file(self, file: Path) -> int:
        """Validate a single workflow file."""
        if not self._validate_file(file):
            print(
                f"File {file} is not accessible, does not exist, "
                f"or is not a valid YAML workflow file."
            )
            return 1

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            progress.add_task(description=f"Validating {file.name}...", total=None)
            result = self._validate_file_with_pipeline(file)

        self.aggregator.add_result(result)
        self._display_result(result)
        self._display_summary()

        return self.aggregator.get_exit_code()

    def _run_directory(self) -> int:
        """Validate all workflow files in the standard .github/workflows directory."""
        project_root = self._find_workflows_directory()
        if not project_root:
            print(
                "Could not find .github/workflows directory. "
                "Please run from your project root or create the directory structure: "
                ".github/workflows/"
            )
            return 1

        directory = project_root / ".github/workflows"
        files = self._find_workflow_files(directory)

        if not files:
            print(
                f"No workflow files (*.yml, *.yaml) found in {directory}. "
                f"Create workflow files or check the directory path."
            )
            return 1

        valid_files = [f for f in files if self._validate_file(f)]
        if not valid_files:
            print(f"No readable workflow files found in {directory}.")
            return 1

        for file in valid_files:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                transient=True,
            ) as progress:
                progress.add_task(description=f"Validating {file.name}...", total=None)
                result = self._validate_file_with_pipeline(file)

            self.aggregator.add_result(result)
            self._display_result(result)

        self._display_summary()
        return self.aggregator.get_exit_code()

    def _display_result(self, result: ValidationResult) -> None:
        """Display validation results for a single file."""
        print(self.formatter.format_file_header(result.file))

        if result.problems.problems:
            for problem in result.problems.problems:
                print(self.formatter.format_problem(problem))
        else:
            print(self.formatter.format_no_problems())

    def _display_summary(self) -> None:
        """Display final summary of all validation results."""
        print(
            self.formatter.format_summary(
                self.aggregator.get_total_errors(),
                self.aggregator.get_total_warnings(),
                self.aggregator.get_max_level(),
            )
        )

    def _find_workflows_directory(self, marker: str = ".github") -> Optional[Path]:
        """Find the project root containing .github directory."""
        start_dir = Path.cwd()
        for directory in [start_dir] + list(start_dir.parents)[:2]:
            if (directory / marker).is_dir():
                return directory
        return None

    def _find_workflow_files(self, directory: Path) -> List[Path]:
        """Find all YAML workflow files in a directory."""
        return list(directory.glob("*.yml")) + list(directory.glob("*.yaml"))

    def _validate_file(self, file_path: Path) -> bool:
        """Validate that file exists, is readable, and has correct extension."""
        try:
            if not file_path.exists() or not file_path.is_file():
                return False

            # Check if file is readable
            file_path.stat()

            # Validate file extension
            if file_path.suffix not in [".yml", ".yaml"]:
                return False

            # Quick check that file is not empty and starts reasonably
            with open(file_path, "r", encoding="utf-8") as f:
                first_line = f.readline()
                return len(first_line.strip()) > 0

        except (OSError, PermissionError, UnicodeDecodeError):
            return False

    def _create_pipeline(self, file: Path) -> DefaultPipeline:
        """Create a new pipeline instance with file-specific fixer."""
        fixer = BaseFixer(file) if self.config.fix else NoFixer()
        return DefaultPipeline(file, self.web_fetcher, fixer)

    def _validate_file_with_pipeline(self, file: Path) -> ValidationResult:
        """Validate a single workflow file using a pipeline and return results."""
        pipeline = self._create_pipeline(file)
        problems = pipeline.process()
        problems.sort()

        # Filter out warnings if quiet mode is enabled
        if self.config.no_warnings:
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
        from validate_actions.globals.problems import ProblemLevel, Problems

        filtered = Problems()
        for problem in problems.problems:
            if problem.level != ProblemLevel.WAR:
                filtered.append(problem)

        return filtered
