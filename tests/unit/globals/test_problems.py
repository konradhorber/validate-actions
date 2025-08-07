"""Unit tests for problem reporting system."""

from validate_actions.globals.problems import Problem, Problems, ProblemLevel
from validate_actions.domain_model.primitives import Pos


class TestProblem:
    """Unit tests for the Problem class."""

    def test_problem_creation(self):
        """Test basic problem creation."""
        pos = Pos(5, 10, 50)
        
        problem = Problem(
            pos=pos,
            level=ProblemLevel.ERR,
            desc="Test error message",
            rule="test_rule"
        )
        
        assert problem.pos == pos
        assert problem.level == ProblemLevel.ERR
        assert problem.desc == "Test error message"
        assert problem.rule == "test_rule"

    def test_problem_different_levels(self):
        """Test problems with different severity levels."""
        pos = Pos(1, 1, 1)
        
        error = Problem(pos, ProblemLevel.ERR, "Error", "rule1")
        warning = Problem(pos, ProblemLevel.WAR, "Warning", "rule2")
        non_problem = Problem(pos, ProblemLevel.NON, "Non-issue", "rule3")
        
        assert error.level == ProblemLevel.ERR
        assert warning.level == ProblemLevel.WAR
        assert non_problem.level == ProblemLevel.NON


class TestProblems:
    """Unit tests for the Problems collection class."""

    def test_problems_creation(self):
        """Test empty problems collection creation."""
        problems = Problems()
        
        assert len(problems.problems) == 0
        assert problems.max_level == ProblemLevel.NON
        assert problems.n_error == 0
        assert problems.n_warning == 0

    def test_problems_append_error(self):
        """Test appending error problem."""
        problems = Problems()
        pos = Pos(1, 1, 1)
        
        error = Problem(pos, ProblemLevel.ERR, "Error message", "error_rule")
        problems.append(error)
        
        assert len(problems.problems) == 1
        assert problems.problems[0] == error
        assert problems.max_level == ProblemLevel.ERR
        assert problems.n_error == 1
        assert problems.n_warning == 0

    def test_problems_append_warning(self):
        """Test appending warning problem."""
        problems = Problems()
        pos = Pos(2, 5, 25)
        
        warning = Problem(pos, ProblemLevel.WAR, "Warning message", "warn_rule")
        problems.append(warning)
        
        assert len(problems.problems) == 1
        assert problems.problems[0] == warning
        assert problems.max_level == ProblemLevel.WAR
        assert problems.n_error == 0
        assert problems.n_warning == 1

    def test_problems_append_non_problem(self):
        """Test appending non-problem (success/fix)."""
        problems = Problems()
        pos = Pos(0, 0, 0)
        
        non_problem = Problem(pos, ProblemLevel.NON, "Fixed issue", "fix_rule")
        problems.append(non_problem)
        
        assert len(problems.problems) == 1
        assert problems.problems[0] == non_problem
        assert problems.max_level == ProblemLevel.NON
        assert problems.n_error == 0
        assert problems.n_warning == 0

    def test_problems_multiple_appends(self):
        """Test appending multiple problems and tracking counts."""
        problems = Problems()
        pos1 = Pos(1, 1, 1)
        pos2 = Pos(2, 2, 20)
        pos3 = Pos(3, 3, 35)
        
        error1 = Problem(pos1, ProblemLevel.ERR, "Error 1", "rule1")
        error2 = Problem(pos2, ProblemLevel.ERR, "Error 2", "rule2")
        warning = Problem(pos3, ProblemLevel.WAR, "Warning", "rule3")
        
        problems.append(error1)
        problems.append(warning)
        problems.append(error2)
        
        assert len(problems.problems) == 3
        assert problems.n_error == 2
        assert problems.n_warning == 1
        assert problems.max_level == ProblemLevel.ERR

    def test_problems_max_level_progression(self):
        """Test that max_level tracks the highest severity."""
        problems = Problems()
        pos = Pos(1, 1, 1)
        
        # Start with NON level
        assert problems.max_level == ProblemLevel.NON
        
        # Add warning - should become max
        warning = Problem(pos, ProblemLevel.WAR, "Warning", "rule1")
        problems.append(warning)
        assert problems.max_level == ProblemLevel.WAR
        
        # Add error - should become max
        error = Problem(pos, ProblemLevel.ERR, "Error", "rule2") 
        problems.append(error)
        assert problems.max_level == ProblemLevel.ERR
        
        # Add another warning - should stay at ERR
        warning2 = Problem(pos, ProblemLevel.WAR, "Another warning", "rule3")
        problems.append(warning2)
        assert problems.max_level == ProblemLevel.ERR

    def test_problems_mixed_levels(self):
        """Test problems collection with all level types."""
        problems = Problems()
        pos = Pos(1, 1, 1)
        
        non_problem = Problem(pos, ProblemLevel.NON, "Fixed", "fix_rule")
        warning = Problem(pos, ProblemLevel.WAR, "Warning", "warn_rule")
        error = Problem(pos, ProblemLevel.ERR, "Error", "err_rule")
        
        problems.append(non_problem)
        problems.append(warning)  
        problems.append(error)
        
        assert len(problems.problems) == 3
        assert problems.n_error == 1
        assert problems.n_warning == 1  
        assert problems.max_level == ProblemLevel.ERR
        
        # Non-problems don't affect counts but are stored
        assert problems.problems[0].level == ProblemLevel.NON

    def test_problems_default_factory(self):
        """Test that problems list uses default factory properly."""
        problems1 = Problems()
        problems2 = Problems()
        
        # Should be separate lists
        pos = Pos(1, 1, 1)
        problem = Problem(pos, ProblemLevel.ERR, "Error", "rule")
        
        problems1.append(problem)
        
        assert len(problems1.problems) == 1
        assert len(problems2.problems) == 0
