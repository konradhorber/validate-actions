"""CLI components for output formatting and result aggregation.

This module provides the building blocks for the CLI interface, including formatters
for colored output and aggregators for collecting results.
"""

from .output_formatter import ColoredFormatter, OutputFormatter
from .result_aggregator import (
    MaxWarningsResultAggregator,
    ResultAggregator,
    StandardResultAggregator,
)

__all__ = [
    "ColoredFormatter",
    "MaxWarningsResultAggregator",
    "OutputFormatter",
    "ResultAggregator",
    "StandardResultAggregator",
]
