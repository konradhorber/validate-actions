from abc import ABC, abstractmethod
from pathlib import Path

from validate_actions.globals.problems import Problem, ProblemLevel


class OutputFormatter(ABC):
    """Interface for formatting CLI output."""

    @abstractmethod
    def format_file_header(self, file: Path) -> str:
        """Format header for a file being validated."""
        pass

    @abstractmethod
    def format_problem(self, problem: Problem) -> str:
        """Format a single problem for display."""
        pass

    @abstractmethod
    def format_no_problems(self) -> str:
        """Format message when no problems found."""
        pass

    @abstractmethod
    def format_summary(
        self, total_errors: int, total_warnings: int, max_level: ProblemLevel
    ) -> str:
        """Format final summary of all validation results."""
        pass


class ColoredFormatter(OutputFormatter):
    """
    Colored console output formatter.

    Formats CLI output with ANSI color codes and consistent spacing.
    Used as the default formatter for interactive terminal sessions.
    """

    STYLE = {
        ProblemLevel.NON: {"color_bold": "\033[1;92m", "color": "\033[92m", "sign": "✓"},
        ProblemLevel.ERR: {"color_bold": "\033[1;31m", "color": "\033[31m", "sign": "✗"},
        ProblemLevel.WAR: {"color_bold": "\033[1;33m", "color": "\033[33m", "sign": "⚠"},
    }

    DEF_STYLE = {
        "format_end": "\033[0m",
        "neutral": "\033[2m",
        "underline": "\033[4m",
    }

    def format_file_header(self, file: Path) -> str:
        """Format file header with underline."""
        return f'\n{self.DEF_STYLE["underline"]}{file}{self.DEF_STYLE["format_end"]}'

    def format_problem(self, problem: Problem) -> str:
        """Format problem with colors and positioning."""
        line = (
            f'  {self.DEF_STYLE["neutral"]}{problem.pos.line + 1}:{problem.pos.col + 1}'
            f'{self.DEF_STYLE["format_end"]}'
        )
        line += max(20 - len(line), 0) * " "

        level_info = self._get_level_info(problem.level)
        line += f'{level_info["color"]}{level_info["name"]}{self.DEF_STYLE["format_end"]}'
        line += max(38 - len(line), 0) * " "
        line += problem.desc

        if problem.rule:
            line += f'  {self.DEF_STYLE["neutral"]}({problem.rule}){self.DEF_STYLE["format_end"]}'

        return line

    def format_no_problems(self) -> str:
        """Format success message when no problems found."""
        return (
            f'  {self.DEF_STYLE["neutral"]}{self.STYLE[ProblemLevel.NON]["sign"]} '
            f'All checks passed{self.DEF_STYLE["format_end"]}'
        )

    def format_summary(
        self, total_errors: int, total_warnings: int, max_level: ProblemLevel
    ) -> str:
        """Format colored summary with counts."""
        style = self.STYLE[max_level]
        total_problems = total_errors + total_warnings

        return (
            f'\n{style["color_bold"]}{style["sign"]} {total_problems} problems '
            f'({total_errors} errors, {total_warnings} warnings){self.DEF_STYLE["format_end"]}\n'
        )

    def _get_level_info(self, level: ProblemLevel) -> dict:
        """Get color and name info for problem level."""
        level_map = {
            ProblemLevel.WAR: {"color": self.STYLE[ProblemLevel.WAR]["color"], "name": "warning"},
            ProblemLevel.ERR: {"color": self.STYLE[ProblemLevel.ERR]["color"], "name": "error"},
            ProblemLevel.NON: {"color": self.STYLE[ProblemLevel.NON]["color"], "name": "fixed"},
        }
        return level_map.get(level, {"color": "", "name": "unknown"})
