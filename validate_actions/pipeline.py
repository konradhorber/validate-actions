"""Pipeline for validating workflow files."""
from abc import ABC, abstractmethod
from pathlib import Path

from validate_actions.pipeline_stages.parser import PyYAMLParser
from validate_actions.pipeline_stages.builder import DefaultBuilder
from validate_actions.pipeline_stages.marketplace_enricher import DefaultMarketPlaceEnricher
from validate_actions.pipeline_stages.job_orderer import DefaultJobOrderer
from validate_actions.pipeline_stages.validator import ExtensibleValidator
from validate_actions.globals.fixer import Fixer
from validate_actions.globals.problems import Problems
from validate_actions.globals.web_fetcher import WebFetcher


class Pipeline(ABC):
    """
    Abstract pipeline for validating a specific workflow file.

    Each pipeline instance is bound to a specific file and contains
    all the necessary components to process that file through the
    validation stages.
    """

    def __init__(self, file: Path, fixer: Fixer) -> None:
        self.file = file
        self.fixer = fixer
        self.problems: Problems = Problems()

    @abstractmethod
    def process(self) -> Problems:
        """
        Process the workflow file and return problems found.

        Returns:
            Problems: A collection of problems found during validation.
        """
        pass


class DefaultPipeline(Pipeline):
    """
    Default 5-stage pipeline implementation for workflow validation.
    
    Processes a workflow file through sequential stages:
    1. PyYAMLParser - Parse YAML to dict
    2. DefaultBuilder - Build AST from dict  
    3. DefaultMarketPlaceEnricher - Fetch action metadata
    4. DefaultJobOrderer - Resolve job dependencies
    5. ExtensibleValidator - Run validation rules
    
    Args:
        file: Path to workflow file to validate
        web_fetcher: Web fetcher for action metadata
        fixer: Fixer for auto-corrections
    """
    
    def __init__(self, file: Path, web_fetcher: WebFetcher, fixer: Fixer):
        super().__init__(file, fixer)
        self.web_fetcher = web_fetcher

        self.parser = PyYAMLParser(self.problems)
        self.builder = DefaultBuilder(self.problems)
        self.marketplace_enricher = DefaultMarketPlaceEnricher(
            web_fetcher, self.problems
        )
        self.job_orderer = DefaultJobOrderer(self.problems)
        self.validator = ExtensibleValidator(self.problems, self.fixer)

    def process(self) -> Problems:
        dict = self.parser.process(self.file)
        workflow = self.builder.process(dict)
        workflow = self.marketplace_enricher.process(workflow)
        workflow = self.job_orderer.process(workflow)
        problems = self.validator.process(workflow)
        return problems
