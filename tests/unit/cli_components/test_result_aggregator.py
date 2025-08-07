"""Unit tests for result aggregation."""

from pathlib import Path

from validate_actions.cli_components.result_aggregator import StandardResultAggregator
from validate_actions.globals.problems import Problem, ProblemLevel, Problems
from validate_actions.globals.validation_result import ValidationResult
from validate_actions.domain_model.primitives import Pos


class TestStandardResultAggregator:
    """Unit tests for StandardResultAggregator."""

    def test_empty_aggregator_initial_state(self):
        """Test that empty aggregator has correct initial state."""
        aggregator = StandardResultAggregator()
        
        assert aggregator.get_total_errors() == 0
        assert aggregator.get_total_warnings() == 0
        assert aggregator.get_max_level() == ProblemLevel.NON
        assert aggregator.get_exit_code() == 0
        assert len(aggregator.get_results()) == 0

    def test_add_result_with_errors(self):
        """Test adding a result with errors."""
        aggregator = StandardResultAggregator()
        
        # Create a result with errors
        problems = Problems()
        problems.append(Problem(
            pos=Pos(1, 1, 0),
            level=ProblemLevel.ERR,
            desc="Test error",
            rule="test_rule"
        ))
        
        result = ValidationResult(
            file=Path("test.yml"),
            problems=problems,
            max_level=problems.max_level,
            error_count=problems.n_error,
            warning_count=problems.n_warning
        )
        
        aggregator.add_result(result)
        
        assert aggregator.get_total_errors() == 1
        assert aggregator.get_total_warnings() == 0
        assert aggregator.get_max_level() == ProblemLevel.ERR
        assert aggregator.get_exit_code() == 1
        assert len(aggregator.get_results()) == 1

    def test_add_result_with_warnings(self):
        """Test adding a result with warnings."""
        aggregator = StandardResultAggregator()
        
        # Create a result with warnings
        problems = Problems()
        problems.append(Problem(
            pos=Pos(1, 1, 0),
            level=ProblemLevel.WAR,
            desc="Test warning",
            rule="test_rule"
        ))
        
        result = ValidationResult(
            file=Path("test.yml"),
            problems=problems,
            max_level=problems.max_level,
            error_count=problems.n_error,
            warning_count=problems.n_warning
        )
        
        aggregator.add_result(result)
        
        assert aggregator.get_total_errors() == 0
        assert aggregator.get_total_warnings() == 1
        assert aggregator.get_max_level() == ProblemLevel.WAR
        assert aggregator.get_exit_code() == 2

    def test_add_multiple_results(self):
        """Test adding multiple results accumulates counts correctly."""
        aggregator = StandardResultAggregator()
        
        # First result with errors
        problems1 = Problems()
        problems1.append(Problem(
            pos=Pos(1, 1, 0),
            level=ProblemLevel.ERR,
            desc="Error 1",
            rule="rule1"
        ))
        problems1.append(Problem(
            pos=Pos(2, 1, 10),
            level=ProblemLevel.ERR,
            desc="Error 2",
            rule="rule2"
        ))
        
        result1 = ValidationResult(
            file=Path("test1.yml"),
            problems=problems1,
            max_level=problems1.max_level,
            error_count=problems1.n_error,
            warning_count=problems1.n_warning
        )
        
        # Second result with warnings
        problems2 = Problems()
        problems2.append(Problem(
            pos=Pos(1, 1, 0),
            level=ProblemLevel.WAR,
            desc="Warning 1",
            rule="rule3"
        ))
        
        result2 = ValidationResult(
            file=Path("test2.yml"),
            problems=problems2,
            max_level=problems2.max_level,
            error_count=problems2.n_error,
            warning_count=problems2.n_warning
        )
        
        aggregator.add_result(result1)
        aggregator.add_result(result2)
        
        assert aggregator.get_total_errors() == 2
        assert aggregator.get_total_warnings() == 1
        assert aggregator.get_max_level() == ProblemLevel.ERR
        assert aggregator.get_exit_code() == 1  # Errors take precedence
        assert len(aggregator.get_results()) == 2

    def test_add_clean_result(self):
        """Test adding a result with no problems."""
        aggregator = StandardResultAggregator()
        
        clean_problems = Problems()
        result = ValidationResult(
            file=Path("clean.yml"),
            problems=clean_problems,
            max_level=clean_problems.max_level,
            error_count=clean_problems.n_error,
            warning_count=clean_problems.n_warning
        )
        
        aggregator.add_result(result)
        
        assert aggregator.get_total_errors() == 0
        assert aggregator.get_total_warnings() == 0
        assert aggregator.get_max_level() == ProblemLevel.NON
        assert aggregator.get_exit_code() == 0
        assert len(aggregator.get_results()) == 1

    def test_exit_code_precedence(self):
        """Test that exit codes follow correct precedence (errors > warnings > success)."""
        aggregator = StandardResultAggregator()
        
        # Add warnings first
        problems_warning = Problems()
        problems_warning.append(Problem(
            pos=Pos(1, 1, 0),
            level=ProblemLevel.WAR,
            desc="Warning",
            rule="warn_rule"
        ))
        
        warning_result = ValidationResult(
            file=Path("warn.yml"),
            problems=problems_warning,
            max_level=problems_warning.max_level,
            error_count=problems_warning.n_error,
            warning_count=problems_warning.n_warning
        )
        
        aggregator.add_result(warning_result)
        assert aggregator.get_exit_code() == 2  # Warnings only
        
        # Add errors - should override warning exit code
        problems_error = Problems()
        problems_error.append(Problem(
            pos=Pos(1, 1, 0),
            level=ProblemLevel.ERR,
            desc="Error",
            rule="err_rule"
        ))
        
        error_result = ValidationResult(
            file=Path("error.yml"),
            problems=problems_error,
            max_level=problems_error.max_level,
            error_count=problems_error.n_error,
            warning_count=problems_error.n_warning
        )
        
        aggregator.add_result(error_result)
        assert aggregator.get_exit_code() == 1  # Errors take precedence

    def test_max_level_tracking(self):
        """Test that max level is tracked correctly across results."""
        aggregator = StandardResultAggregator()
        
        # Start with clean result
        clean_problems = Problems()
        clean_result = ValidationResult(
            file=Path("clean.yml"),
            problems=clean_problems,
            max_level=clean_problems.max_level,
            error_count=clean_problems.n_error,
            warning_count=clean_problems.n_warning
        )
        aggregator.add_result(clean_result)
        assert aggregator.get_max_level() == ProblemLevel.NON
        
        # Add warning
        problems_warning = Problems()
        problems_warning.append(Problem(
            pos=Pos(1, 1, 0),
            level=ProblemLevel.WAR,
            desc="Warning",
            rule="warn_rule"
        ))
        warning_result = ValidationResult(
            file=Path("warn.yml"),
            problems=problems_warning,
            max_level=problems_warning.max_level,
            error_count=problems_warning.n_error,
            warning_count=problems_warning.n_warning
        )
        aggregator.add_result(warning_result)
        assert aggregator.get_max_level() == ProblemLevel.WAR
        
        # Add error - should become max level
        problems_error = Problems()
        problems_error.append(Problem(
            pos=Pos(1, 1, 0),
            level=ProblemLevel.ERR,
            desc="Error",
            rule="err_rule"
        ))
        error_result = ValidationResult(
            file=Path("error.yml"),
            problems=problems_error,
            max_level=problems_error.max_level,
            error_count=problems_error.n_error,
            warning_count=problems_error.n_warning
        )
        aggregator.add_result(error_result)
        assert aggregator.get_max_level() == ProblemLevel.ERR
