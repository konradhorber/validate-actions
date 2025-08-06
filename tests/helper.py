import tempfile
from pathlib import Path
from typing import Any, Optional, Tuple

import validate_actions
from validate_actions.building import (
    events_builder,
    jobs_builder,
    marketplace_enricher,
    shared_components_builder,
    steps_builder,
    workflow_builder,
)
from validate_actions.core import problems
from validate_actions.core.web_fetcher import IWebFetcher
from validate_actions.domain_model import contexts
from validate_actions.building import job_orderer
from validate_actions.parsing import parser


class TestWebFetcher(IWebFetcher):
    """Test web fetcher that returns predictable test data instead of making real HTTP requests."""
    
    def fetch(self, url: str) -> Optional[Any]:
        """Return mock response for test actions."""
        # Mock response class
        class MockResponse:
            def __init__(self, status_code: int, text: str = "", json_data: Any = None):
                self.status_code = status_code
                self.text = text
                self._json_data = json_data
            
            def json(self):
                if self._json_data is not None:
                    return self._json_data
                raise ValueError("No JSON data")
        
        # Return test data for known actions
        if "actions/checkout" in url:
            if url.endswith("action.yml") or url.endswith("action.yaml"):
                action_yml = """
name: Checkout
description: Checkout a Git repository
inputs:
  repository:
    description: Repository name
    default: ${{ github.repository }}
  token:
    description: GitHub token
    default: ${{ github.token }}
outputs:
  ref:
    description: The branch, tag or SHA that was checked out
"""
                return MockResponse(200, action_yml)
            elif "/tags" in url:
                tags = [
                    {"name": "v4.2.2", "commit": {"sha": "abc123"}},
                    {"name": "v4.2.1", "commit": {"sha": "def456"}},
                    {"name": "v4.0.0", "commit": {"sha": "ghi789"}},
                ]
                return MockResponse(200, json_data=tags)
        
        elif "actions/setup-node" in url:
            if url.endswith("action.yml") or url.endswith("action.yaml"):
                action_yml = """
name: Setup Node.js
description: Setup Node.js
inputs:
  node-version:
    description: Node.js version
    required: false
"""
                return MockResponse(200, action_yml)
            elif "/tags" in url:
                tags = [
                    {"name": "v4.0.3", "commit": {"sha": "node123"}},
                    {"name": "v4.0.2", "commit": {"sha": "node456"}},
                    {"name": "v3.8.1", "commit": {"sha": "node789"}},
                ]
                return MockResponse(200, json_data=tags)
        
        elif "actions/cache" in url:
            if url.endswith("action.yml") or url.endswith("action.yaml"):
                action_yml = """
name: Cache
description: Cache dependencies
inputs:
  path:
    description: Cache path
    required: true
  key:
    description: Cache key
    required: true
"""
                return MockResponse(200, action_yml)
            elif "/tags" in url:
                tags = [
                    {"name": "v3.3.2", "commit": {"sha": "cache123"}},
                    {"name": "v3.3.1", "commit": {"sha": "cache456"}},
                    {"name": "v2.1.7", "commit": {"sha": "cache789"}},
                ]
                return MockResponse(200, json_data=tags)
        
        elif "8398a7/action-slack" in url:
            if url.endswith("action.yml") or url.endswith("action.yaml"):
                action_yml = """
name: Slack
description: Send Slack notifications
inputs:
  status:
    description: Job status
    required: true
  webhook_url:
    description: Slack webhook URL
    required: false
  channel:
    description: Slack channel
    required: false
  fields:
    description: Custom fields
    required: false
  custom_payload:
    description: Custom payload
    required: false
"""
                return MockResponse(200, action_yml)
            elif "/tags" in url:
                tags = [{"name": "v3.0.0", "commit": {"sha": "xyz789"}}]
                return MockResponse(200, json_data=tags)
                
        elif "actions/stale" in url:
            if url.endswith("action.yml") or url.endswith("action.yaml"):
                action_yml = """
name: Stale
description: Mark stale issues and pull requests
inputs:
  repo-token:
    description: Repository token
    default: ${{ github.token }}
"""
                return MockResponse(200, action_yml)
            elif "/tags" in url:
                tags = [{"name": "v9.0.0", "commit": {"sha": "stale123"}}]
                return MockResponse(200, json_data=tags)
        
        elif "action/is-unknown" in url:
            # Return 404 for unknown actions to simulate real behavior
            return MockResponse(404, "Not Found")
        
        # Default: return None (no response)
        return None
    
    def clear_cache(self) -> None:
        """Clear cache (no-op for test implementation)."""
        pass


def parse_workflow_string(
    workflow_string: str,
) -> Tuple[validate_actions.domain_model.ast.Workflow, problems.Problems]:
    """
    Helper function to parse a workflow string into a Workflow object.

    Args:
        workflow_string (str): The workflow YAML content as a string

    Returns:
        Tuple[Workflow, List[LintProblem]]: The parsed workflow and any
        problems found
    """
    with tempfile.NamedTemporaryFile(suffix=".yml", mode="w+", delete=False) as temp_file:
        temp_file.write(workflow_string)
        temp_file_path = Path(temp_file.name)

    try:
        problems_instance = problems.Problems()
        yaml_parser = parser.PyYAMLParser(problems_instance)
        contexts_instance = contexts.Contexts()
        shared_components_builder_instance = shared_components_builder.SharedComponentsBuilder(problems_instance)
        events_builder_instance = events_builder.EventsBuilder(problems_instance)
        steps_builder_instance = steps_builder.StepsBuilder(problems_instance, contexts_instance, shared_components_builder_instance)
        jobs_builder_instance = jobs_builder.JobsBuilder(
            problems_instance, steps_builder_instance, contexts_instance, shared_components_builder_instance
        )
        job_orderer_instance = job_orderer.JobOrderer(problems_instance)

        # Parse the workflow file first
        workflow_dict = yaml_parser.process(temp_file_path)
        
        # Build workflow from parsed dict
        director = workflow_builder.WorkflowBuilder(
            problems_instance,
            events_builder_instance,
            jobs_builder_instance,
            contexts_instance,
            shared_components_builder_instance,
        )
        workflow = director.process(workflow_dict)
        
        # Add web marketplace metadata to actions
        test_web_fetcher = TestWebFetcher()
        marketplace_enricher_instance = marketplace_enricher.MarketPlaceEnricher(test_web_fetcher, problems_instance)
        workflow = marketplace_enricher_instance.process(workflow)
        
        # Prepare workflow with job dependency analysis and needs contexts
        workflow = job_orderer_instance.process(workflow)
        
        return workflow, problems_instance
    finally:
        temp_file_path.unlink(missing_ok=True)
