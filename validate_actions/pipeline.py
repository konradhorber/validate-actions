from abc import ABC, abstractmethod
from pathlib import Path

from validate_actions import pipeline_stages
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
    def __init__(self, file: Path, web_fetcher: WebFetcher, fixer: Fixer):
        super().__init__(file, fixer)
        self.web_fetcher = web_fetcher

        self.parser = pipeline_stages.PyYAMLParser(self.problems)
        self.builder = pipeline_stages.DefaultBuilder(self.problems)
        self.marketplace_enricher = pipeline_stages.DefaultMarketPlaceEnricher(
            web_fetcher, self.problems
        )
        self.job_orderer = pipeline_stages.DefaultJobOrderer(self.problems)
        self.validator = pipeline_stages.ExtensibleValidator(self.problems, self.fixer)

    def process(self) -> Problems:
        dict = self.parser.process(self.file)
        workflow = self.builder.process(dict)
        workflow = self.marketplace_enricher.process(workflow)
        workflow = self.job_orderer.process(workflow)
        problems = self.validator.process(workflow)
        return problems
