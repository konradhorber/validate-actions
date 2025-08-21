"""Output formatter interface and implementations for CLI validation results."""
from abc import ABC, abstractmethod
from pathlib import Path

from rich.console import Console
from rich.text import Text

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


class RichFormatter(OutputFormatter):
    """
    Modern Rich-based formatter with clean, minimalist styling.

    Features:
    - Clean typography with subtle colors
    - Consistent spacing and alignment
    - Modern icons and visual hierarchy
    - Responsive layout that works in any terminal width
    """

    def __init__(self):
        """Initialize with Rich console."""
        self.console = Console()

        # Modern color palette - subtle and professional
        self.colors = {
            ProblemLevel.NON: "bright_green",
            ProblemLevel.ERR: "bright_red",
            ProblemLevel.WAR: "yellow",
            "muted": "bright_black",
            "accent": "cyan",
            "text": "white",
        }

        # Modern icons
        self.icons = {
            ProblemLevel.NON: "✓",
            ProblemLevel.ERR: "✕",
            ProblemLevel.WAR: "⚠",
            "file": "📁",
        }

    def format_file_header(self, file: Path) -> str:
        """Format clean file header with modern styling."""
        # Truncate path to show only filename and at most 2 levels up
        parts = file.parts
        if len(parts) > 3:  # More than 2 directories + filename
            display_path = str(Path(*parts[-3:]))  # Take last 2 dirs + filename
        else:
            display_path = str(file)

        # Create file header with icon and clean typography
        header_text = Text()
        header_text.append(f"{self.icons['file']} ", style=self.colors["muted"])
        header_text.append(display_path, style=f"bold {self.colors['accent']}")

        # Use console to render to string
        with self.console.capture() as capture:
            self.console.print(header_text)
        return f"\n{capture.get()}"

    def format_problem(self, problem: Problem) -> str:
        """Format problem with clean typography and smart alignment."""
        # Build the line with Rich styling
        line = Text()

        # Position (muted, right-aligned in a fixed width)
        position = f"{problem.pos.line + 1}:{problem.pos.col + 1}"
        line.append(f"{position:>8} ", style=self.colors["muted"])

        # Level indicator with icon
        level_color = self.colors.get(problem.level, self.colors["text"])
        level_name = self._get_level_name(problem.level)
        icon = self.icons.get(problem.level, "•")

        line.append(f"{icon} ", style=level_color)
        line.append(f"{level_name:<7} ", style=f"{level_color}")

        # Description
        line.append(str(problem.desc), style=self.colors["text"])

        # Rule name (muted, if present)
        if problem.rule:
            line.append(f"  ({problem.rule})", style=self.colors["muted"])

        # Render to string
        with self.console.capture() as capture:
            self.console.print(line)
        return capture.get().rstrip()

    def format_no_problems(self) -> str:
        """Format success message with clean styling."""
        success_text = Text()
        success_text.append(
            f"  {self.icons[ProblemLevel.NON]} ", style=self.colors[ProblemLevel.NON]
        )
        success_text.append("All checks passed", style=f"bold {self.colors[ProblemLevel.NON]}")

        with self.console.capture() as capture:
            self.console.print(success_text)
        return capture.get()

    def format_summary(
        self, total_errors: int, total_warnings: int, max_level: ProblemLevel
    ) -> str:
        """Format modern summary with visual hierarchy."""
        total_problems = total_errors + total_warnings

        if total_problems == 0:
            # Clean success summary
            summary = Text()
            summary.append(
                f"\n{self.icons[ProblemLevel.NON]} ", style=self.colors[ProblemLevel.NON]
            )
            summary.append(
                "Validation completed successfully", style=f"bold {self.colors[ProblemLevel.NON]}"
            )
            summary.append(" - no issues found\n", style=self.colors["muted"])
        else:
            # Create a clean summary table
            summary = Text()
            summary.append("\n")

            # Main status line
            icon = self.icons.get(max_level, "•")
            color = self.colors.get(max_level, self.colors["text"])

            summary.append(f"{icon} ", style=color)
            summary.append("Validation completed", style=f"bold {color}")
            issue_text = f" - {total_problems} issue"
            if total_problems != 1:
                issue_text += "s"
            issue_text += " found"
            summary.append(issue_text, style=color)

            # Breakdown
            if total_errors > 0:
                summary.append(
                    f"\n  {self.icons[ProblemLevel.ERR]} ", style=self.colors[ProblemLevel.ERR]
                )
                error_text = f"{total_errors} error"
                if total_errors != 1:
                    error_text += "s"
                summary.append(error_text, style=self.colors[ProblemLevel.ERR])

            if total_warnings > 0:
                summary.append(
                    f"\n  {self.icons[ProblemLevel.WAR]} ", style=self.colors[ProblemLevel.WAR]
                )
                warning_text = f"{total_warnings} warning"
                if total_warnings != 1:
                    warning_text += "s"
                summary.append(warning_text, style=self.colors[ProblemLevel.WAR])

            summary.append("\n")

        # Render to string
        with self.console.capture() as capture:
            self.console.print(summary)
        return capture.get()

    def _get_level_name(self, level: ProblemLevel) -> str:
        """Get display name for problem level."""
        level_names = {
            ProblemLevel.WAR: "warning",
            ProblemLevel.ERR: "error",
            ProblemLevel.NON: "fixed",
        }
        return level_names.get(level, "unknown")
