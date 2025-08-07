"""CLI components for output formatting, result aggregation, and validation services.

This module provides the building blocks for the CLI interface, including formatters
for colored output, aggregators for collecting results, and validation services that
orchestrate the pipeline.
"""

from .output_formatter import ColoredFormatter, OutputFormatter
from .result_aggregator import ResultAggregator, StandardResultAggregator
from .validation_service import StandardValidationService, ValidationService

__all__ = [
    "ColoredFormatter",
    "OutputFormatter", 
    "ResultAggregator",
    "StandardResultAggregator",
    "StandardValidationService",
    "ValidationService",
]
