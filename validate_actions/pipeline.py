from abc import abstractmethod
from pathlib import Path

from validate_actions import pipeline_stages
from validate_actions.globals.fixer import Fixer
from validate_actions.globals.problems import Problems
from validate_actions.globals.process_stage import ProcessStage
from validate_actions.globals.web_fetcher import IWebFetcher


class IPipeline(ProcessStage[Path, Problems]):
    """
    Interface for Validator classes.

    Classes implementing this interface should provide a `run` method
    to validate workflow files and return problems found.
    """

    def __init__(self, fixer: Fixer) -> None:
        self.problems: Problems = Problems()
        self.fixer = fixer

    @abstractmethod
    def process(self, file: Path) -> Problems:
        """
        Validate a workflow file and return problems found.

        Args:
            file (Path): Path to the workflow file to validate.
            fix (bool): Whether to attempt automatic fixes for detected problems.

        Returns:
            Problems: A collection of problems found during validation.
        """
        pass


class Pipeline(IPipeline):
    def __init__(self, web_fetcher: IWebFetcher, fixer: Fixer):
        super().__init__(fixer)
        self.web_fetcher = web_fetcher

        self.parser = pipeline_stages.PyYAMLParser(self.problems)
        self.builder = pipeline_stages.Builder(self.problems)
        self.marketplace_enricher = pipeline_stages.MarketPlaceEnricher(web_fetcher, self.problems)
        self.job_orderer = pipeline_stages.JobOrderer(self.problems)
        self.validator = pipeline_stages.ExtensibleValidator(self.problems, self.fixer)

    def process(self, path: Path) -> Problems:
        dict = self.parser.process(path)
        workflow = self.builder.process(dict)
        workflow = self.marketplace_enricher.process(workflow)
        workflow = self.job_orderer.process(workflow)
        problems = self.validator.process(workflow)
        return problems
