from dataclasses import dataclass, field
from enum import Enum
from typing import List

from validate_actions.domain_model.primitives import Pos


class ProblemLevel(Enum):
    """Linting problem levels"""

    NON = 0
    WAR = 1
    ERR = 2


@dataclass
class Problem:
    pos: Pos
    level: ProblemLevel
    desc: str
    rule: str


@dataclass
class Problems:
    problems: List[Problem] = field(default_factory=list)
    max_level: ProblemLevel = ProblemLevel.NON
    n_error: int = 0
    n_warning: int = 0

    def append(self, problem: Problem) -> None:
        self.problems.append(problem)
        match problem.level:
            case ProblemLevel.WAR:
                self.n_warning += 1
            case ProblemLevel.ERR:
                self.n_error += 1
            case ProblemLevel.NON:
                # Non-problem, do not count
                pass
        self.max_level = ProblemLevel(max(self.max_level.value, problem.level.value))

    def sort(self) -> None:
        self.problems.sort(key=lambda x: (x.pos.line, x.pos.col))

    def extend(self, problems: "Problems") -> None:
        self.problems.extend(problems.problems)
        self.n_error += problems.n_error
        self.n_warning += problems.n_warning
        self.max_level = ProblemLevel(max(self.max_level.value, problems.max_level.value))

    def remove(self, problem: Problem) -> None:
        self.problems.remove(problem)
        match problem.level:
            case ProblemLevel.WAR:
                self.n_warning -= 1
            case ProblemLevel.ERR:
                self.n_error -= 1
            case ProblemLevel.NON:
                # Non-problem, do not count
                pass
        if not self.problems:
            self.max_level = ProblemLevel.NON
