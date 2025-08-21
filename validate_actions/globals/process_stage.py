"""Defines basic interface of pipeline stages."""
from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from validate_actions.globals.problems import Problems

# Generic type variables for input and output
TInput = TypeVar("TInput")
TOutput = TypeVar("TOutput")


class ProcessStage(ABC, Generic[TInput, TOutput]):
    """Interface for processing stages in the validation pipeline.

    All processing stages are instantiated with a Problems collection and provide
    a single method that takes one generic input and returns one generic output.
    """

    def __init__(self, problems: Problems) -> None:
        """Initialize processing stage with problems collection.

        Args:
            problems: Problems collection to store any issues found during processing
        """
        self.problems = problems

    @abstractmethod
    def process(self, input_data: TInput) -> TOutput:
        """Process input data and return output.

        Args:
            input_data: Generic input to process

        Returns:
            Generic processed output
        """
        pass
