"""Core global utilities and types for validate-actions."""

from .cli_config import CLIConfig
from .fixer import Fixer
from .problems import Problem, ProblemLevel, Problems
from .process_stage import ProcessStage
from .validation_result import ValidationResult
from .web_fetcher import CachedWebFetcher, WebFetcher

__all__ = [
    "CLIConfig",
    "Fixer",
    "Problem",
    "ProblemLevel",
    "Problems",
    "ProcessStage",
    "ValidationResult",
    "WebFetcher",
    "CachedWebFetcher",
]
