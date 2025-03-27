import validateactions.linter
import sys

class Format:
    @staticmethod
    def standard_color(problem, filename):
        line = f'  \033[2m{problem.line + 1}:{problem.column + 1}\033[0m'
        line += max(20 - len(line), 0) * ' '
        if problem.level == 'warning':
            line += f'\033[33m{problem.level}\033[0m'
        else:
            line += f'\033[31m{problem.level}\033[0m'
        line += max(38 - len(line), 0) * ' '
        line += problem.desc
        if problem.rule:
            line += f'  \033[2m({problem.rule})\033[0m'
        return line

def run_directory(directory):
    max_level = 0
    total_errors = 0
    total_warnings = 0

    prob_level = 0
    files = list(directory.glob('*.yml')) + list(directory.glob('*.yaml'))
    for file in files:
        prob_level, n_errors, n_warnings = run(file)
        max_level = max(max_level, validateactions.linter.PROBLEM_LEVELS[prob_level])
        total_errors += n_errors
        total_warnings += n_warnings
    
    if max_level == validateactions.linter.PROBLEM_LEVELS['error']:
        return_code = 1
    elif max_level == validateactions.linter.PROBLEM_LEVELS['warning']:
        return_code = 2
    else:
        return_code = 0

    show_return_message(return_code, total_errors, total_warnings)

    sys.exit(return_code)


def run(file):
    try:
        with open(file, newline='') as f:
            problems = validateactions.linter.run(f)
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
    first = True

    for problem in problems:
        max_level = max(max_level, validateactions.linter.PROBLEM_LEVELS[problem.level])
        if first:
            print()
            print(f'\033[4m{file}\033[0m')
            first = False
        print(Format.standard_color(problem, file))
    
    problem_level = validateactions.linter.PROBLEM_LEVELS[max_level]
    return problem_level

def show_return_message(return_code, n_error, n_warning):
    if return_code == 0:
        color_begin = '\033[1;92m'  # bold + bright green
        sign = '✓'
    elif return_code == 1:
        color_begin = '\033[1;31m'  # bold + red
        sign = '✗'
    else:
        color_begin = '\033[1;33m'  # bold + yellow
        sign = '⚠'

    color_end = '\033[0m'

    print()
    print(f'{color_begin}{sign} {n_error+n_warning} problems ({n_error} errors, {n_warning} warnings){color_end}')
    print()