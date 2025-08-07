"""Tests for MarketPlaceEnricher component."""

from tests.conftest import parse_workflow_string
from tests.unit.globals.test_web_fetcher import TestWebFetcher
from validate_actions.domain_model.ast import ExecAction
from validate_actions.globals.problems import ProblemLevel, Problems
from validate_actions.pipeline_stages.marketplace_enricher import MarketPlaceEnricher


class TestMarketplaceEnricher:
    def test_unknown_action_generates_warning(self):
        """Test that unknown actions generate warnings during enrichment."""
        workflow_string = """
name: test
on: push
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Notify Slack
        uses: action/is-unknown@vtest
        with:
          unknown_input: 'test'
"""
        workflow, problems = parse_workflow_string(workflow_string)

        # Check that marketplace enricher generates warnings for unknown actions
        unknown_action_problems = [
            p
            for p in problems.problems
            if "unknown" in p.desc.lower() and p.rule == "marketplace-enricher"
        ]
        assert len(unknown_action_problems) >= 1
        assert unknown_action_problems[0].level == ProblemLevel.WAR


    def test_known_action_gets_metadata(self):
        """Test that known actions get enriched with metadata."""
        workflow_string = """
name: test
on: push
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4
"""
        workflow, problems = parse_workflow_string(workflow_string)

        # Find the checkout action
        build_job = None
        for job_name, job in workflow.jobs_.items():
            if job_name.string == "build":
                build_job = job
                break

        assert build_job is not None
        checkout_step = build_job.steps_[0]
        assert isinstance(checkout_step.exec, ExecAction)
        assert checkout_step.exec.metadata is not None

        # Check that metadata was populated
        metadata = checkout_step.exec.metadata
        assert len(metadata.possible_inputs) > 0  # Should have inputs like 'repository', 'token'
        assert len(metadata.outputs) > 0  # Should have outputs like 'ref'
        assert len(metadata.version_tags) > 0  # Should have version tags


    def test_marketplace_enricher_direct_usage(self):
        """Test MarketPlaceEnricher directly with a test web fetcher."""
        problems = Problems()
        test_web_fetcher = TestWebFetcher()
        enricher = MarketPlaceEnricher(test_web_fetcher, problems)

        # Create a simple workflow with an action
        workflow_string = """
name: test
on: push
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
"""
        workflow, parsing_problems = parse_workflow_string(workflow_string)

        # Clear problems from parsing to isolate enricher problems
        problems.problems.clear()

        # Run enricher
        enriched_workflow = enricher.process(workflow)

        # Verify enrichment happened
        build_job = None
        for job_name, job in enriched_workflow.jobs_.items():
            if job_name.string == "build":
                build_job = job
                break

        assert build_job is not None
        checkout_step = build_job.steps_[0]
        assert isinstance(checkout_step.exec, ExecAction)
        assert checkout_step.exec.metadata is not None

        metadata = checkout_step.exec.metadata
        assert "repository" in metadata.possible_inputs
        assert "token" in metadata.possible_inputs
        assert "ref" in metadata.outputs
        assert len(metadata.version_tags) == 3  # Our test data has 3 tags


    def test_marketplace_enricher_handles_missing_action(self):
        """Test MarketPlaceEnricher handles missing actions gracefully."""
        problems = Problems()
        test_web_fetcher = TestWebFetcher()
        enricher = MarketPlaceEnricher(test_web_fetcher, problems)

        # Create workflow with unknown action
        workflow_string = """
name: test
on: push
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: unknown/nonexistent@v1
"""
        workflow, parsing_problems = parse_workflow_string(workflow_string)

        # Clear problems from parsing to isolate enricher problems
        problems.problems.clear()

        # Run enricher
        enriched_workflow = enricher.process(workflow)

        # Should have generated warning problems
        assert len(problems.problems) >= 1
        warning_problems = [p for p in problems.problems if p.level == ProblemLevel.WAR]
        assert len(warning_problems) >= 1
        assert any("metadata" in p.desc.lower() for p in warning_problems)

        # Action should still have metadata but with empty data
        build_job = None
        for job_name, job in enriched_workflow.jobs_.items():
            if job_name.string == "build":
                build_job = job
                break

        assert build_job is not None
        unknown_step = build_job.steps_[0]
        assert isinstance(unknown_step.exec, ExecAction)
        assert unknown_step.exec.metadata is not None

        # Metadata should be empty for unknown actions
        metadata = unknown_step.exec.metadata
        assert len(metadata.possible_inputs) == 0
        assert len(metadata.outputs) == 0
