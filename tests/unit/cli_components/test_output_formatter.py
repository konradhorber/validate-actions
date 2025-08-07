"""Unit tests for output formatting."""

from pathlib import Path

from validate_actions.cli_components.output_formatter import ColoredFormatter
from validate_actions.domain_model.primitives import Pos
from validate_actions.globals.problems import Problem, ProblemLevel


class TestColoredFormatter:
    """Unit tests for ColoredFormatter output formatting."""

    def test_format_file_header(self):
        """Test file header formatting includes underline and path."""
        formatter = ColoredFormatter()
        file_path = Path("/test/workflow.yml")

        header = formatter.format_file_header(file_path)

        assert str(file_path) in header
        assert "\033[4m" in header  # underline code
        assert "\033[0m" in header  # reset code

    def test_format_problem_error(self):
        """Test error problem formatting includes position, level, and description."""
        formatter = ColoredFormatter()
        problem = Problem(
            desc="Invalid action reference",
            level=ProblemLevel.ERR,
            pos=Pos(10, 5, 150),
            rule="test_rule",
        )

        formatted = formatter.format_problem(problem)

        assert "11:6" in formatted  # line:col (1-based)
        assert "Invalid action reference" in formatted
        assert "test_rule" in formatted
        assert "\033[31m" in formatted  # red color for errors

    def test_format_problem_warning(self):
        """Test warning problem formatting uses warning colors."""
        formatter = ColoredFormatter()
        problem = Problem(
            desc="Outdated action version",
            level=ProblemLevel.WAR,
            pos=Pos(5, 10, 75),
            rule="version_check",
        )

        formatted = formatter.format_problem(problem)

        assert "6:11" in formatted  # line:col (1-based)
        assert "Outdated action version" in formatted
        assert "version_check" in formatted
        assert "\033[33m" in formatted  # yellow color for warnings

    def test_format_problem_without_rule_display(self):
        """Test problem formatting displays rule information."""
        formatter = ColoredFormatter()
        problem = Problem(
            pos=Pos(1, 1, 0), level=ProblemLevel.ERR, desc="General issue", rule="general_check"
        )

        formatted = formatter.format_problem(problem)

        assert "General issue" in formatted
        assert "2:2" in formatted  # line:col (1-based)
        assert "general_check" in formatted
        assert "(" in formatted  # Should contain parentheses for rule

    def test_format_no_problems(self):
        """Test success message formatting when no problems found."""
        formatter = ColoredFormatter()

        message = formatter.format_no_problems()

        assert "All checks passed" in message
        assert "✓" in message
        assert "\033[2m" in message  # neutral color

    def test_format_summary_errors_only(self):
        """Test summary formatting when only errors are present."""
        formatter = ColoredFormatter()

        summary = formatter.format_summary(
            total_errors=3, total_warnings=0, max_level=ProblemLevel.ERR
        )

        assert "3" in summary
        assert "error" in summary.lower()
        assert "\033[1;31m" in summary  # bold red for errors

    def test_format_summary_warnings_only(self):
        """Test summary formatting when only warnings are present."""
        formatter = ColoredFormatter()

        summary = formatter.format_summary(
            total_errors=0, total_warnings=2, max_level=ProblemLevel.WAR
        )

        assert "2" in summary
        assert "warning" in summary.lower()
        assert "\033[1;33m" in summary  # bold yellow for warnings

    def test_format_summary_mixed(self):
        """Test summary formatting with both errors and warnings."""
        formatter = ColoredFormatter()

        summary = formatter.format_summary(
            total_errors=2, total_warnings=5, max_level=ProblemLevel.ERR
        )

        assert "2" in summary
        assert "5" in summary
        assert "error" in summary.lower()
        assert "warning" in summary.lower()
        assert "\033[1;31m" in summary  # Should use error color for max level

    def test_format_summary_no_issues(self):
        """Test summary formatting when no issues are found."""
        formatter = ColoredFormatter()

        summary = formatter.format_summary(
            total_errors=0, total_warnings=0, max_level=ProblemLevel.NON
        )

        assert "0" in summary or "no" in summary.lower()
        assert "\033[1;92m" in summary  # bold green for success
