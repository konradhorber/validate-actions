"""
Job ordering domain models for GitHub Actions workflows.

This module contains dataclasses that represent job execution plans, conditions,
stages, and dependencies for workflow analysis.
"""

from dataclasses import dataclass, field
from typing import Dict, List

from validate_actions.domain_model.ast import Job


@dataclass
class JobCondition:
    """Represents conditional execution information for a job."""

    expression: str
    depends_on_success: List[str] = field(default_factory=list)
    depends_on_failure: List[str] = field(default_factory=list)
    always_run: bool = False


@dataclass
class JobStage:
    """Represents a stage of parallel job execution."""

    parallel_jobs: List[Job] = field(default_factory=list)


@dataclass
class JobExecutionPlan:
    """Represents the complete execution plan for a workflow."""

    stages: List[JobStage] = field(default_factory=list)
    conditional_jobs: Dict[str, JobCondition] = field(default_factory=dict)
    dependency_graph: Dict[str, List[str]] = field(default_factory=dict)


@dataclass
class CyclicDependency:
    """Represents a circular dependency error."""

    job_ids: List[str] = field(default_factory=list)
