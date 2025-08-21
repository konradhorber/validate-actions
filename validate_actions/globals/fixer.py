"""Fixer module for applying changes to YAML workflow files."""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List

from validate_actions.globals.problems import Problem, ProblemLevel


class Fixer(ABC):
    """Abstract base for applying fixes to YAML workflow files."""

    @abstractmethod
    def edit_yaml_at_position(
        self, idx: int, old_text: str, new_text: str, problem: Problem, new_problem_desc: str
    ) -> Problem:
        """Queue an edit to replace text at a specific character position.

        Args:
            idx: Character index where replacement starts
            old_text: Text to be replaced (for validation)
            new_text: Replacement text
            problem: Problem instance to update
            new_problem_desc: New description for the fixed problem

        Returns:
            Updated problem instance
        """
        pass

    @abstractmethod
    def flush(self) -> None:
        """Apply all queued edits to the file."""
        pass


class BaseFixer(Fixer):
    """Default fixer that batches edits and applies them on flush."""

    file_path: Path
    pending_edits: List[Dict[str, Any]]

    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.pending_edits = []

    def edit_yaml_at_position(
        self, idx: int, old_text: str, new_text: str, problem: Problem, new_problem_desc: str
    ) -> Problem:
        """Queue an edit for later application and mark problem as fixed.

        Args:
            idx: Character index where replacement starts
            old_text: Text to be replaced (for validation)
            new_text: Replacement text
            problem: Problem instance to update
            new_problem_desc: New description for the fixed problem

        Returns:
            Updated problem instance with NON level
        """
        # Batch the edit instead of applying immediately
        edit = {
            "idx": idx,
            "num_delete": len(old_text),
            "new_text": new_text,
            "problem": problem,
            "new_problem_desc": new_problem_desc,
        }
        self.pending_edits.append(edit)

        # Update problem to reflect that it will be fixed
        problem.level = ProblemLevel.NON
        problem.desc = new_problem_desc

        return problem

    def flush(self) -> None:
        """Apply all pending edits to the file in descending position order."""
        if not self.pending_edits:
            return

        try:
            # Read current file content
            with open(self.file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Sort edits by position in descending order (end-of-file to beginning)
            # This ensures later edits don't affect the positions of earlier edits
            sorted_edits = sorted(self.pending_edits, key=lambda edit: edit["idx"], reverse=True)

            # Apply edits in descending position order
            for edit in sorted_edits:
                idx = edit["idx"]
                num_delete = edit["num_delete"]
                new_text = edit["new_text"]

                # Validate position bounds
                if idx < 0 or idx > len(content):
                    continue

                # Apply edit: delete and insert
                content = content[:idx] + new_text + content[idx + num_delete :]

            # Write updated content back to file
            with open(self.file_path, "w", encoding="utf-8") as f:
                f.write(content)

            # Clear pending edits after successful application
            self.pending_edits.clear()

        except (OSError, UnicodeError):
            # On error, leave pending_edits intact for potential retry
            pass


class NoFixer(Fixer):
    """A fixer that does nothing. Used when no fixes are needed."""

    def edit_yaml_at_position(
        self, idx: int, old_text: str, new_text: str, problem: Problem, new_problem_desc: str
    ) -> Problem:
        """No-op implementation that returns the problem unchanged.

        Args:
            idx: Character index (ignored)
            old_text: Text to be replaced (ignored)
            new_text: Replacement text (ignored)
            problem: Problem instance to return
            new_problem_desc: New description (ignored)

        Returns:
            Unmodified problem instance
        """
        # No-op, just return the problem as is
        return problem

    def flush(self) -> None:
        """No-op implementation with no effects."""
        # No-op, nothing to flush
        pass
