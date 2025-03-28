import validate_actions.linter
import sys

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


class Format:
    @staticmethod
    def standard_color(problem, filename):
        line = f'  {STYLE["neutral"]}{problem.line + 1}:{problem.column + 1}{STYLE["format_end"]}'
        line += max(20 - len(line), 0) * ' '
        if problem.level == 'warning':
            line += f'{STYLE[2]["color"]}{problem.level}{STYLE["format_end"]}'
        else:
            line += f'{STYLE[1]["color"]}{problem.level}{STYLE["format_end"]}'
        line += max(38 - len(line), 0) * ' '
        line += problem.desc
        if problem.rule:
            line += f'  {STYLE["neutral"]}({problem.rule}){STYLE["format_end"]}'
        return line

def run_directory(directory):
    max_level = 0
    total_errors = 0
    total_warnings = 0

    prob_level = 0
    files = list(directory.glob('*.yml')) + list(directory.glob('*.yaml'))
    for file in files:
        prob_level, n_errors, n_warnings = run(file)
        max_level = max(max_level, validate_actions.linter.PROBLEM_LEVELS[prob_level])
        total_errors += n_errors
        total_warnings += n_warnings
    
    if max_level == validate_actions.linter.PROBLEM_LEVELS['error']:
        return_code = 1
    elif max_level == validate_actions.linter.PROBLEM_LEVELS['warning']:
        return_code = 2
    else:
        return_code = 0

    show_return_message(return_code, total_errors, total_warnings)

    sys.exit(return_code)


def run(file):
    try:
        with open(file, newline='') as f:
            problems = validate_actions.linter.run(f)
    except OSError as e:
        print(e, file=sys.stderr)
        sys.exit(-1)

    sorted_problems = sorted(problems, key=lambda x: (x.line, x.column))
    
    prob_level = show_problems(sorted_problems, file)

    n_error = sum(1 for p in sorted_problems if p.level == 'error')
    n_warning = sum(1 for p in sorted_problems if p.level == 'warning')

    return prob_level, n_error, n_warning
    
def show_problems(problems, file):
    max_level = 0

    print()
    print(f'\033[4m{file}\033[0m')

    for problem in problems:
        max_level = max(max_level, validate_actions.linter.PROBLEM_LEVELS[problem.level])
        print(Format.standard_color(problem, file))

    if max_level == 0:
        print(f'  {STYLE["neutral"]}{STYLE[0]["sign"]} All checks passed\033[0m')
    
    problem_level = validate_actions.linter.PROBLEM_LEVELS[max_level]
    return problem_level

def show_return_message(return_code, n_error, n_warning):
    style = STYLE[return_code]

    print()
    print(f'{style["color_bold"]}{style["sign"]} {n_error+n_warning} problems ({n_error} errors, {n_warning} warnings){STYLE["format_end"]}')
    print()