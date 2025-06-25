from abc import ABC, abstractmethod
from pathlib import Path

from validate_actions.problems import Problem, ProblemLevel


class Fixer(ABC):
    @abstractmethod
    def edit_yaml_at_position(
        self, idx: int, num_delete: int, new_text: str, problem: Problem, new_problem_desc: str
    ) -> Problem:
        pass


class BaseFixer(Fixer):
    file_path: Path
    shifted: int = 0

    def __init__(self, file_path: Path, shifted: int = 0):
        self.file_path = file_path
        self.shifted = shifted

    def edit_yaml_at_position(
        self, idx: int, num_delete: int, new_text: str, problem: Problem, new_problem_desc: str
    ) -> Problem:
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                content = f.read()

            idx += self.shifted

            if idx < 0 or idx >= len(content):
                return problem

            # Perform edit: delete and insert
            updated_content = content[:idx] + new_text + content[idx + num_delete :]

            with open(self.file_path, "w", encoding="utf-8") as f:
                f.write(updated_content)

            self.shifted += len(new_text) - num_delete

            problem.level = ProblemLevel.NON
            problem.desc = new_problem_desc

        except (OSError, ValueError, TypeError, UnicodeError):
            return problem
        finally:
            return problem
