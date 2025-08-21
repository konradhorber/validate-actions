"""Validator coordinating rules and fixer."""
import importlib
import os
from abc import abstractmethod
from typing import List, Optional

import yaml

from validate_actions.domain_model import ast
from validate_actions.globals.fixer import Fixer
from validate_actions.globals.problems import Problems
from validate_actions.globals.process_stage import ProcessStage
from validate_actions.rules.rule import Rule


class Validator(ProcessStage[ast.Workflow, Problems]):
    """Validates GitHub Actions workflows by applying complex checks."""
    @abstractmethod
    def process(self, workflow: ast.Workflow) -> Problems:
        """Validate the given workflow and return any problems found.

        Args:
            workflow: The workflow to validate.

        Returns:
            A Problems object containing any issues found during validation.
        """
        pass


class ExtensibleValidator(Validator):
    """
    Validates GitHub Actions workflows by applying a configurable set of rules.

    The ExtensibleValidator uses a YAML configuration file to determine which rules to apply,
    making it easily extensible without code changes. Rules are loaded dynamically
    using the module:class format.

    Example config file (rules/rules.yml):
        rules:
          expressions-contexts: validate_actions.rules.expressions_contexts:ExpressionsContexts
          action-metadata: validate_actions.rules.action_metadata:ActionMetadata
          custom-rule: my_package.rules.custom:MyCustomRule

    Usage:
        # Use default config
        validator = ExtensibleValidator(problems, fixer)

        # Use custom config
        validator = ExtensibleValidator(problems, fixer, "/path/to/custom-rules.yml")
    """

    def __init__(
        self, problems: Problems, fixer: Fixer, config_path: Optional[str] = None
    ) -> None:
        """
        Initialize the validator with a problems collector, fixer, and optional config path.

        Args:
            problems: Problems collector to store validation issues
            fixer: Fixer instance for auto-correcting issues
            config_path: Optional path to rules config file. If None, uses default location.
        """
        super().__init__(problems)
        self.fixer = fixer
        self.config_path = config_path or self._get_default_config_path()

    def _get_default_config_path(self) -> str:
        """
        Get the default path to the rules configuration file.

        Returns:
            Path to the default rules.yml file in the rules directory.
        """
        current_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(current_dir, "..", "rules", "rules.yml")

    def _load_rules_from_config(self, workflow: ast.Workflow) -> List[Rule]:
        """
        Load and instantiate rules from the configuration file.

        The config file should contain a 'rules' section mapping rule names to
        module:class paths in the format 'package.module:ClassName'.

        Args:
            workflow: The workflow AST to pass to rule constructors

        Returns:
            List of instantiated Rule objects ready for validation

        Raises:
            FileNotFoundError: If the config file doesn't exist
            yaml.YAMLError: If the config file has invalid YAML syntax
            ImportError: If a rule module cannot be imported
            AttributeError: If a rule class cannot be found in its module
        """
        with open(self.config_path, "r") as f:
            config = yaml.safe_load(f)

        rules = []
        for class_path in config["rules"].values():
            module_path, class_name = class_path.split(":")
            module = importlib.import_module(module_path)
            rule_class = getattr(module, class_name)
            rules.append(rule_class(workflow=workflow, fixer=self.fixer))

        return rules

    def process(self, workflow: ast.Workflow) -> Problems:
        """Validate the given workflow and return any problems found.

        Args:
            workflow: The workflow to validate.

        Returns:
            A Problems object containing any issues found during validation.
        """
        rules = self._load_rules_from_config(workflow)

        for rule in rules:
            for problem in rule.check():
                self.problems.append(problem)

        # Apply all batched fixes (NoFixer will do nothing if fixing is disabled)
        self.fixer.flush()
        return self.problems
