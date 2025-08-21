"""Builder stage that transformes parsed YAML data into a structured AST."""
from abc import abstractmethod
from typing import Any, Dict

from validate_actions.domain_model.ast import Workflow
from validate_actions.domain_model.contexts import Contexts
from validate_actions.domain_model.primitives import String
from validate_actions.globals.problems import Problems
from validate_actions.globals.process_stage import ProcessStage
from validate_actions.pipeline_stages.builders.events_builder import DefaultEventsBuilder
from validate_actions.pipeline_stages.builders.jobs_builder import DefaultJobsBuilder
from validate_actions.pipeline_stages.builders.shared_components_builder import (
    DefaultSharedComponentsBuilder,
)
from validate_actions.pipeline_stages.builders.steps_builder import DefaultStepsBuilder
from validate_actions.pipeline_stages.builders.workflow_builder import DefaultWorkflowBuilder


class Builder(ProcessStage[Dict[String, Any], Workflow]):
    """Abstract base class for workflow AST builders.

    The Builder stage transforms parsed YAML data into a structured AST
    representation that can be used for validation and analysis.
    """

    @abstractmethod
    def process(self, workflow_dict: Dict[String, Any]) -> Workflow:
        """Build a workflow AST from parsed YAML data.

        Args:
            workflow_dict: Dictionary representation of the parsed workflow YAML,
                         with String keys preserving position information

        Returns:
            Workflow: Complete AST representation of the GitHub Actions workflow
        """
        pass


class DefaultBuilder(Builder):
    """Default implementation of the Builder stage for GitHub Actions workflows.
    
    This class orchestrates the construction of a complete workflow AST by coordinating
    multiple specialized builders. It creates and manages builders for different workflow
    components (events, jobs, steps, shared components) and delegates the actual AST
    construction to a workflow builder.
    
    The builder follows a hierarchical structure where:
    - Workflow contains events and jobs
    - Jobs contain steps and shared components
    - Steps use shared components and contexts
    
    Attributes:
        shared_components_builder (DefaultSharedComponentsBuilder): Builds reusable workflow components
        events_builder (DefaultEventsBuilder): Builds workflow trigger events (push, pull_request, etc.)
        steps_builder (DefaultStepsBuilder): Builds individual job steps with actions and commands
        jobs_builder (DefaultJobsBuilder): Builds job definitions with their steps and configuration
        workflow_builder (DefaultWorkflowBuilder): Top-level builder that orchestrates all components
    """
    
    def __init__(self, problems: Problems) -> None:
        """Initialize the DefaultBuilder with all necessary sub-builders.
        
        Creates a complete builder hierarchy with shared contexts and problem reporting.
        All builders share the same Problems instance for centralized issue tracking.
        
        Args:
            problems (Problems): Shared problems collection for reporting validation issues
        """
        super().__init__(problems)

        # Create shared contexts for expression validation and variable resolution
        contexts = Contexts()
        
        # Initialize builders in dependency order
        self.shared_components_builder = DefaultSharedComponentsBuilder(problems)
        self.events_builder = DefaultEventsBuilder(problems)
        self.steps_builder = DefaultStepsBuilder(
            problems, contexts, self.shared_components_builder
        )
        self.jobs_builder = DefaultJobsBuilder(
            problems, self.steps_builder, contexts, self.shared_components_builder
        )

        # Create the top-level workflow builder with all dependencies
        self.workflow_builder = DefaultWorkflowBuilder(
            problems=problems,
            events_builder=self.events_builder,
            jobs_builder=self.jobs_builder,
            contexts=contexts,
            shared_components_builder=self.shared_components_builder,
        )

    def process(self, workflow_dict: Dict[String, Any]) -> Workflow:
        """Build a complete workflow AST from parsed YAML data.
        
        Delegates the AST construction to the workflow builder, which coordinates
        all sub-builders to create a fully structured representation of the workflow.
        
        Args:
            workflow_dict (Dict[String, Any]): Dictionary representation of parsed workflow YAML,
                                             with String keys that preserve position information
                                             
        Returns:
            Workflow: Complete AST representation of the GitHub Actions workflow,
                     including all events, jobs, steps, and shared components
        """
        return self.workflow_builder.process(workflow_dict)
