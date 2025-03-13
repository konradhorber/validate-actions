import linter
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
    
def run(file):
    try:
        with open(file, newline='') as f:
            problems = linter.run(f)
    except OSError as e:
        print(e, file=sys.stderr)
        sys.exit(-1)
    
    prob_level = show_problems(problems, file)

    if prob_level == linter.PROBLEM_LEVELS['error']:
        return_code = 1
    elif prob_level == linter.PROBLEM_LEVELS['warning']:
        return_code = 2
    else:
        return_code = 0

    
    sys.exit(return_code)

    
def show_problems(problems, file):
    max_level = 0
    first = True

    for problem in problems:
        max_level = max(max_level, linter.PROBLEM_LEVELS[problem.level])
        if first:
            print(f'\033[4m{file}\033[0m')
            first = False
        print(Format.standard_color(problem, file))

    return max_level