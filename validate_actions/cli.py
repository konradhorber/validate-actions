import sys
from pathlib import Path
from typing import List, Tuple, Union

import typer
from rich.progress import Progress, SpinnerColumn, TextColumn

from validate_actions import linter
from validate_actions.lint_problem import LintProblem


class CLI:
    STYLE = {
        0: {
            'color_bold': '\033[1;92m',
            'color': '\033[92m',
            'sign': '✓'
        },
        1: {
            'color_bold': '\033[1;31m',
            'color': '\033[31m',
            'sign': '✗'
        },
        2: {
            'color_bold': '\033[1;33m',
            'color': '\033[33m',
            'sign': '⚠'
        },
        'format_end': '\033[0m',
        'neutral': '\033[2m',
    }

    def start(self) -> None:
        project_root = self.find_workflows()
        if not project_root:
            print(
                f'{self.STYLE["neutral"]}Could not find workflows directory. '
                f'Please run this script from the root of your project.'
                f'{self.STYLE["format_end"]}'
            )
            raise typer.Exit(1)
        directory = project_root / '.github/workflows'
        self.run_directory(directory)

    def find_workflows(self, marker='.github') -> Union[Path, None]:
        start_dir = Path.cwd()
        for directory in [start_dir] + list(start_dir.parents)[:2]:
            if (directory / marker).is_dir():
                return directory
        return None

    def run_directory(self, directory: Path) -> None:
        max_level = 0
        total_errors = 0
        total_warnings = 0

        prob_level = 0
        files = list(directory.glob('*.yml')) + list(directory.glob('*.yaml'))
        for file in files:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                transient=True
            ) as progress:
                progress.add_task(description=f'Validating {file.name}...', total=None)
                prob_level, n_errors, n_warnings = self.run(file)
            max_level = max(max_level, linter.PROBLEM_LEVELS[prob_level])
            total_errors += n_errors
            total_warnings += n_warnings

        if max_level == linter.PROBLEM_LEVELS['error']:
            return_code = 1
        elif max_level == linter.PROBLEM_LEVELS['warning']:
            return_code = 2
        else:
            return_code = 0

        self.show_return_message(return_code, total_errors, total_warnings)

        sys.exit(return_code)

    def run(self, file: Path) -> Tuple[int, int, int]:
        problems = linter.run(file)

        sorted_problems = sorted(problems, key=lambda x: (x.line, x.column))

        prob_level = self.show_problems(sorted_problems, file)

        n_error = sum(1 for p in sorted_problems if p.level == 'error')
        n_warning = sum(1 for p in sorted_problems if p.level == 'warning')

        return prob_level, n_error, n_warning

    def show_problems(self, problems: List[LintProblem], file: Path) -> int:
        max_level = 0

        print()
        print(f'\033[4m{file}\033[0m')

        for problem in problems:
            max_level = max(max_level, linter.PROBLEM_LEVELS[problem.level])
            print(self.standard_color(problem, file))

        if max_level == 0:
            print(
                f'  {self.STYLE["neutral"]}{self.STYLE[0]["sign"]} All checks passed\033[0m'
            )

        problem_level = linter.PROBLEM_LEVELS[max_level]
        return problem_level

    def show_return_message(self, return_code: int, n_error: int, n_warning: int) -> None:
        style = self.STYLE[return_code]

        print()
        print(
            f'{style["color_bold"]}{style["sign"]} {n_error+n_warning} problems '
            f'({n_error} errors, {n_warning} warnings){self.STYLE["format_end"]}'
        )
        print()

    def standard_color(self, problem: LintProblem, filename: Path) -> str:
        line = (
            f'  {self.STYLE["neutral"]}{problem.line + 1}:{problem.column + 1}'
            f'{self.STYLE["format_end"]}'
        )
        line += max(20 - len(line), 0) * ' '
        if problem.level == 'warning':
            line += f'{self.STYLE[2]["color"]}{problem.level}{self.STYLE["format_end"]}'
        else:
            line += f'{self.STYLE[1]["color"]}{problem.level}{self.STYLE["format_end"]}'
        line += max(38 - len(line), 0) * ' '
        line += problem.desc
        if problem.rule:
            line += (
                f'  {self.STYLE["neutral"]}({problem.rule}){self.STYLE["format_end"]}'
            )
        return line
