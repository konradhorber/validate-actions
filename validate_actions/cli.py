import sys
from pathlib import Path
from typing import Tuple

import typer
from rich.progress import Progress, SpinnerColumn, TextColumn

from validate_actions.problems import Problem, ProblemLevel, Problems
from validate_actions.validator import Validator


class CLI:
    STYLE = {
        ProblemLevel.NON: {"color_bold": "\033[1;92m", "color": "\033[92m", "sign": "✓"},
        ProblemLevel.ERR: {"color_bold": "\033[1;31m", "color": "\033[31m", "sign": "✗"},
        ProblemLevel.WAR: {"color_bold": "\033[1;33m", "color": "\033[33m", "sign": "⚠"},
    }
    DEF_STYLE = {
        "format_end": "\033[0m",
        "neutral": "\033[2m",
    }

    def start(self, fix: bool) -> None:
        project_root = self.find_workflows()
        if not project_root:
            print(
                f'{self.DEF_STYLE["neutral"]}Could not find workflows directory. '
                f"Please run this script from the root of your project."
                f'{self.DEF_STYLE["format_end"]}'
            )
            raise typer.Exit(1)
        directory = project_root / ".github/workflows"
        self.run_directory(directory, fix)

    def find_workflows(self, marker=".github"):
        start_dir = Path.cwd()
        for directory in [start_dir] + list(start_dir.parents)[:2]:
            if (directory / marker).is_dir():
                return directory
        return None

    def run_directory(self, directory: Path, fix: bool) -> None:
        max_level = ProblemLevel.NON
        total_errors = 0
        total_warnings = 0

        prob_level: ProblemLevel
        files = list(directory.glob("*.yml")) + list(directory.glob("*.yaml"))
        for file in files:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                transient=True,
            ) as progress:
                progress.add_task(description=f"Validating {file.name}...", total=None)
                prob_level, n_errors, n_warnings = self.run(file, fix)
            max_level = ProblemLevel(max(max_level.value, prob_level.value))
            total_errors += n_errors
            total_warnings += n_warnings

        self.show_end_msg(max_level, total_errors, total_warnings)

        match max_level:
            case ProblemLevel.NON:
                return_code = 0
            case ProblemLevel.WAR:
                return_code = 2
            case ProblemLevel.ERR:
                return_code = 1
            case _:
                raise ValueError(f"Invalid problem level: {max_level}")

        sys.exit(return_code)

    def run(self, file: Path, fix: bool) -> Tuple[ProblemLevel, int, int]:
        problems = Validator.run(file, fix)

        problems.sort()

        self.show_problems(problems, file)

        return problems.max_level, problems.n_error, problems.n_warning

    def show_problems(self, problems: Problems, file: Path) -> None:
        print()
        print(f"\033[4m{file}\033[0m")

        for problem in problems.problems:
            print(self.standard_color(problem, file))

        if problems.max_level == ProblemLevel.NON:
            print(
                f'  {self.DEF_STYLE["neutral"]}{self.STYLE[ProblemLevel.NON]["sign"]} All checks '
                f"passed\033[0m"
            )

    def standard_color(self, problem: Problem, filename: Path) -> str:
        line = (
            f'  {self.DEF_STYLE["neutral"]}{problem.pos.line + 1}:{problem.pos.col + 1}'
            f'{self.DEF_STYLE["format_end"]}'
        )
        line += max(20 - len(line), 0) * " "
        war = ProblemLevel.WAR
        err = ProblemLevel.ERR
        non = ProblemLevel.NON
        if problem.level == war:
            level_str = "warning"
            line += f'{self.STYLE[war]["color"]}{level_str}{self.DEF_STYLE["format_end"]}'
        elif problem.level == err:
            level_str = "error"
            line += f'{self.STYLE[err]["color"]}{level_str}{self.DEF_STYLE["format_end"]}'
        elif problem.level == non:
            level_str = "fixed"
            line += f'{self.STYLE[non]["color"]}{level_str}{self.DEF_STYLE["format_end"]}'
        line += max(38 - len(line), 0) * " "
        line += problem.desc
        if problem.rule:
            line += f'  {self.DEF_STYLE["neutral"]}({problem.rule}){self.DEF_STYLE["format_end"]}'
        return line

    def show_end_msg(self, max_level: ProblemLevel, n_error: int, n_warning: int) -> None:
        style = self.STYLE[max_level]

        print()
        print(
            f'{style["color_bold"]}{style["sign"]} {n_error+n_warning} problems '
            f'({n_error} errors, {n_warning} warnings){self.DEF_STYLE["format_end"]}'
        )
        print()
