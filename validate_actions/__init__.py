"""validate-actions: GitHub Actions workflow validation and linting CLI tool.

This package provides tools for validating GitHub Actions workflows, detecting errors,
and automatically fixing common issues. It can be used both as a CLI tool and as a
Python library.

Example:
    CLI usage:
        $ validate-actions                    # Validate all workflows
        $ validate-actions workflow.yml      # Validate specific file  
        $ validate-actions --fix             # Auto-fix issues
        
    Library usage:
        from validate_actions import validate_workflow, Problem, ProblemLevel
        
        problems = validate_workflow('workflow.yml')
        for problem in problems.problems:
            print(f"{problem.level}: {problem.desc}")
"""

from .cli import CLI, StandardCLI
from .globals import Problem, ProblemLevel, Problems, ValidationResult
from .pipeline import IPipeline, Pipeline

# High-level validation function for library usage
def validate_workflow(filepath: str, fix: bool = False) -> Problems:
    """Validate a GitHub Actions workflow file.
    
    Args:
        filepath: Path to the workflow YAML file
        fix: Whether to attempt automatic fixes
        
    Returns:
        Problems: Collection of validation issues found
    """
    from pathlib import Path
    from .globals import Fixer, WebFetcher
    
    web_fetcher = WebFetcher()
    fixer = Fixer(Path(filepath)) if fix else None
    pipeline = Pipeline(web_fetcher, fixer)
    
    return pipeline.process(Path(filepath))

__all__ = [
    # Main validation function
    "validate_workflow",
    
    # Core types
    "Problem", 
    "ProblemLevel",
    "Problems",
    "ValidationResult",
    
    # CLI interface
    "CLI",
    "StandardCLI",
    
    # Pipeline
    "IPipeline", 
    "Pipeline",
]
