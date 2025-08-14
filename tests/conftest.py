"""Shared test configuration and fixtures for validate-actions tests."""

import tempfile
from pathlib import Path
from typing import Tuple

import pytest

import validate_actions
from validate_actions.domain_model import contexts
from validate_actions.globals import problems
from validate_actions.pipeline_stages import job_orderer, marketplace_enricher, parser
from validate_actions.pipeline_stages.builders import (
    events_builder,
    jobs_builder,
    shared_components_builder,
    steps_builder,
    workflow_builder,
)


@pytest.fixture
def sample_workflow():
    """Standard valid workflow for testing."""
    return """
name: Test Workflow
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4
      - name: Setup Node
        uses: actions/setup-node@v4
        with:
          node-version: '18'
"""


@pytest.fixture
def invalid_workflow():
    """Workflow with known validation errors for testing."""
    return """
name: Invalid Workflow
on:
  push:
    branches: [ $default-branch ]
  pullrequest:
    branches: [ $default-branch ]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Notify Slack
        uses: 8398a7/action-slack
        with:
          unknown_input: 'test'
      - name: Notify Slack
        uses: 8398a7/action-slack@v3
        with:
          status: 'test'
"""


@pytest.fixture
def mock_web_fetcher():
    """Mock web fetcher with predictable responses."""
    from tests.unit.globals.test_web_fetcher import TestWebFetcher

    return TestWebFetcher()


@pytest.fixture
def temp_workflow_file():
    """Create a temporary workflow file for testing."""

    def _create_temp_file(content: str) -> Path:
        temp_file = tempfile.NamedTemporaryFile(suffix=".yml", mode="w+", delete=False)
        temp_file.write(content)
        temp_file.close()
        return Path(temp_file.name)

    return _create_temp_file


@pytest.fixture
def test_problems():
    """Empty problems collection for testing."""
    return problems.Problems()


@pytest.fixture
def test_contexts():
    """Test contexts instance."""
    return contexts.Contexts()


def parse_workflow_string(
    workflow_string: str,
) -> Tuple[validate_actions.domain_model.ast.Workflow, problems.Problems]:
    """
    Helper function to parse a workflow string into a Workflow object.

    Args:
        workflow_string (str): The workflow YAML content as a string

    Returns:
        Tuple[Workflow, Problems]: The parsed workflow and any
        problems found
    """
    with tempfile.NamedTemporaryFile(suffix=".yml", mode="w+", delete=False) as temp_file:
        temp_file.write(workflow_string)
        temp_file_path = Path(temp_file.name)

    try:
        problems_instance = problems.Problems()
        yaml_parser = parser.PyYAMLParser(problems_instance)
        contexts_instance = contexts.Contexts()
        shared_components_builder_instance = (
            shared_components_builder.DefaultSharedComponentsBuilder(problems_instance)
        )
        events_builder_instance = events_builder.DefaultEventsBuilder(problems_instance)
        steps_builder_instance = steps_builder.DefaultStepsBuilder(
            problems_instance, contexts_instance, shared_components_builder_instance
        )
        jobs_builder_instance = jobs_builder.DefaultJobsBuilder(
            problems_instance,
            steps_builder_instance,
            contexts_instance,
            shared_components_builder_instance,
        )
        job_orderer_instance = job_orderer.DefaultJobOrderer(problems_instance)

        # Parse the workflow file first
        workflow_dict = yaml_parser.process(temp_file_path)

        # Build workflow from parsed dict
        director = workflow_builder.DefaultWorkflowBuilder(
            problems_instance,
            events_builder_instance,
            jobs_builder_instance,
            contexts_instance,
            shared_components_builder_instance,
        )
        workflow = director.process(workflow_dict)

        # Add web marketplace metadata to actions
        from tests.unit.globals.test_web_fetcher import TestWebFetcher

        test_web_fetcher = TestWebFetcher()
        marketplace_enricher_instance = marketplace_enricher.DefaultMarketPlaceEnricher(
            test_web_fetcher, problems_instance
        )
        workflow = marketplace_enricher_instance.process(workflow)

        # Prepare workflow with job dependency analysis and needs contexts
        workflow = job_orderer_instance.process(workflow)

        return workflow, problems_instance
    finally:
        temp_file_path.unlink(missing_ok=True)
