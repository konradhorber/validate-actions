"""Handles problem management for validate-actions."""
from dataclasses import dataclass, field
from enum import Enum
from typing import List

from validate_actions.domain_model.primitives import Pos


class ProblemLevel(Enum):
    """Enumeration of problem severity levels for workflow validation.
    
    This enum defines the different levels of issues that can be found
    during workflow validation, ordered by severity.
    
    Attributes:
        NON (int): No problem or informational level (severity 0)
        WAR (int): Warning level - potential issues that don't break functionality (severity 1)
        ERR (int): Error level - critical issues that need to be fixed (severity 2)
    """

    NON = 0  # No problem/informational
    WAR = 1  # Warning level
    ERR = 2  # Error level


@dataclass
class Problem:
    """Represents a single validation problem found in a workflow file.
    
    This class encapsulates all information about a specific issue discovered
    during workflow validation, including its location, severity, description,
    and the rule that detected it.
    
    Attributes:
        pos (Pos): Position information (line, column, character index) where the problem occurs
        level (ProblemLevel): Severity level of the problem (NON, WAR, or ERR)
        desc (str): Human-readable description of the problem
        rule (str): Name/identifier of the validation rule that detected this problem
    """
    pos: Pos
    level: ProblemLevel
    desc: str
    rule: str


@dataclass
class Problems:
    """Collection and management of validation problems.
    
    This class manages a collection of Problem instances, maintains counts
    by severity level, and tracks the highest severity level encountered.
    It provides methods for adding, removing, sorting, and merging problems.
    
    Attributes:
        problems (List[Problem]): List of all problems found during validation
        max_level (ProblemLevel): Highest severity level among all problems
        n_error (int): Count of problems with ERROR level
        n_warning (int): Count of problems with WARNING level
    """
    problems: List[Problem] = field(default_factory=list)
    max_level: ProblemLevel = ProblemLevel.NON
    n_error: int = 0
    n_warning: int = 0

    def append(self, problem: Problem) -> None:
        """Add a new problem to the collection and update counts.
        
        Appends the problem to the internal list, increments the appropriate
        severity counter, and updates the maximum severity level if necessary.
        
        Args:
            problem (Problem): The problem instance to add to the collection
        """
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
        """Sort problems by their position in the file.
        
        Sorts the problems list in-place by line number first, then by column number.
        This ensures problems are presented in the order they appear in the source file.
        """
        self.problems.sort(key=lambda x: (x.pos.line, x.pos.col))

    def extend(self, problems: "Problems") -> None:
        """Merge another Problems collection into this one.
        
        Extends the current problems list with all problems from another collection,
        updates all counters, and adjusts the maximum severity level.
        
        Args:
            problems (Problems): Another Problems instance to merge into this one
        """
        self.problems.extend(problems.problems)
        self.n_error += problems.n_error
        self.n_warning += problems.n_warning
        self.max_level = ProblemLevel(max(self.max_level.value, problems.max_level.value))

    def remove(self, problem: Problem) -> None:
        """Remove a specific problem from the collection.
        
        Removes the problem from the list, decrements the appropriate severity counter,
        and resets max_level to NON if no problems remain.
        
        Args:
            problem (Problem): The specific problem instance to remove
            
        Raises:
            ValueError: If the problem is not found in the collection
        """
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
