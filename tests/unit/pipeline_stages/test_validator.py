"""Tests for the ExtensibleValidator class."""

import os
import tempfile
import textwrap
from unittest.mock import Mock

import pytest
import yaml

from validate_actions.domain_model import ast
from validate_actions.globals.fixer import NoFixer
from validate_actions.globals.problems import Problems
from validate_actions.pipeline_stages.validator import ExtensibleValidator
from validate_actions.rules.rule import Rule


class MockRule(Rule):
    """Mock rule for testing purposes."""

    def __init__(self, workflow: ast.Workflow, fixer):
        super().__init__(workflow, fixer)
        self.check_called = False

    def check(self):
        self.check_called = True
        yield from []


class TestExtensibleValidator:
    """Test cases for ExtensibleValidator."""

    def test_default_config_path(self):
        """Test that default config path points to rules/rules.yml."""
        problems = Problems()
        fixer = NoFixer()
        validator = ExtensibleValidator(problems, fixer)

        assert validator.config_path.endswith("rules/rules.yml")
        assert os.path.exists(validator.config_path)

    def test_custom_config_path(self):
        """Test using a custom config file path."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            config = {
                "rules": {
                    "test-rule": "validate_actions.rules.expressions_contexts:ExpressionsContexts"
                }
            }
            yaml.dump(config, f)
            config_path = f.name

        try:
            problems = Problems()
            fixer = NoFixer()
            validator = ExtensibleValidator(problems, fixer, config_path)

            assert validator.config_path == config_path
        finally:
            os.unlink(config_path)

    def test_load_rules_from_config(self):
        """Test that rules are correctly loaded from config file."""
        config_content = textwrap.dedent(
            """
            rules:
              expressions-contexts: validate_actions.rules.expressions_contexts:ExpressionsContexts
              action-metadata: validate_actions.rules.action_metadata:ActionMetadata
        """
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            f.write(config_content)
            config_path = f.name

        try:
            problems = Problems()
            fixer = NoFixer()
            validator = ExtensibleValidator(problems, fixer, config_path)

            # Create a mock workflow
            workflow = Mock(spec=ast.Workflow)

            # Load rules from config
            rules = validator._load_rules_from_config(workflow)

            assert len(rules) == 2
            assert all(isinstance(rule, Rule) for rule in rules)
        finally:
            os.unlink(config_path)

    def test_load_rules_invalid_module(self):
        """Test error handling when module cannot be imported."""
        config_content = textwrap.dedent(
            """
            rules:
              invalid-rule: nonexistent.module:NonexistentClass
        """
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            f.write(config_content)
            config_path = f.name

        try:
            problems = Problems()
            fixer = NoFixer()
            validator = ExtensibleValidator(problems, fixer, config_path)
            workflow = Mock(spec=ast.Workflow)

            with pytest.raises(ImportError):
                validator._load_rules_from_config(workflow)
        finally:
            os.unlink(config_path)

    def test_load_rules_invalid_class(self):
        """Test error handling when class cannot be found in module."""
        config_content = textwrap.dedent(
            """
            rules:
              invalid-class: validate_actions.rules.expressions_contexts:NonexistentClass
        """
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            f.write(config_content)
            config_path = f.name

        try:
            problems = Problems()
            fixer = NoFixer()
            validator = ExtensibleValidator(problems, fixer, config_path)
            workflow = Mock(spec=ast.Workflow)

            with pytest.raises(AttributeError):
                validator._load_rules_from_config(workflow)
        finally:
            os.unlink(config_path)

    def test_process_with_default_config(self):
        """Test the full validation process using default config."""
        problems = Problems()
        fixer = NoFixer()
        validator = ExtensibleValidator(problems, fixer)

        # Create a minimal workflow AST with required attributes
        workflow = Mock(spec=ast.Workflow)
        workflow.jobs = []
        workflow.jobs_ = {}
        workflow.contexts = []
        workflow.workflow_calls = []
        workflow.reusable_workflow_calls = []

        # Process should complete without errors
        result = validator.process(workflow)

        assert result is problems
        # We don't assert on specific problem counts since they depend on the actual rules

    def test_process_with_mock_rules(self):
        """Test validation process with mock rules to verify rule execution."""
        # Create config with mock rule (this is a bit contrived since we need a
        # real importable class)
        config_content = textwrap.dedent(
            """
            rules:
              expressions-contexts: validate_actions.rules.expressions_contexts:ExpressionsContexts
        """
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            f.write(config_content)
            config_path = f.name

        try:
            problems = Problems()
            fixer = NoFixer()
            validator = ExtensibleValidator(problems, fixer, config_path)

            # Create a minimal workflow AST with required attributes
            workflow = Mock(spec=ast.Workflow)
            workflow.jobs = []
            workflow.jobs_ = {}
            workflow.contexts = []
            workflow.workflow_calls = []
            workflow.reusable_workflow_calls = []

            result = validator.process(workflow)
            assert result is problems
        finally:
            os.unlink(config_path)

    def test_config_file_not_found(self):
        """Test error handling when config file doesn't exist."""
        problems = Problems()
        fixer = NoFixer()
        validator = ExtensibleValidator(problems, fixer, "/nonexistent/config.yml")
        workflow = Mock(spec=ast.Workflow)

        with pytest.raises(FileNotFoundError):
            validator._load_rules_from_config(workflow)

    def test_invalid_yaml_config(self):
        """Test error handling when config file has invalid YAML."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            f.write("invalid: yaml: content: [")  # Invalid YAML
            config_path = f.name

        try:
            problems = Problems()
            fixer = NoFixer()
            validator = ExtensibleValidator(problems, fixer, config_path)
            workflow = Mock(spec=ast.Workflow)

            with pytest.raises(yaml.YAMLError):
                validator._load_rules_from_config(workflow)
        finally:
            os.unlink(config_path)
