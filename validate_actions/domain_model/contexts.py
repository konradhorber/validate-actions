"""GitHub Actions context definitions and type system.

This module defines the context objects available in GitHub Actions workflows for
expression validation. Contexts provide access to workflow runtime information,
environment state, and inter-job communication.

Contexts are organized hierarchically and each property has a defined type for
validation purposes. The type system supports GitHub Actions' dynamic nature
while enabling static analysis.

See GitHub's official documentation:
https://docs.github.com/en/actions/learn-github-actions/contexts
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional

# =============================================================================
# TYPE SYSTEM
# =============================================================================


@dataclass(frozen=True)
class ContextType(Enum):
    """Type system for GitHub Actions context values.

    Defines the possible types that context properties can have.
    Used for expression validation and type checking.
    """

    string = auto()  # Text values
    boolean = auto()  # true/false values
    object = auto()  # Complex objects with properties
    number = auto()  # Numeric values


# =============================================================================
# GITHUB CONTEXT
# =============================================================================


@dataclass
class GithubContext:
    """GitHub context - contains information about the workflow run.

    The github context contains information about the workflow run and the
    event that triggered the run.
    You can read most of the github context data in environment variables.

    Ordered according to GitHub's official documentation.
    """

    type_: Optional[ContextType] = ContextType.object

    # Action-related properties
    action: Optional[ContextType] = ContextType.string
    action_path: Optional[ContextType] = ContextType.string
    action_ref: Optional[ContextType] = ContextType.string
    action_repository: Optional[ContextType] = ContextType.string
    action_status: Optional[ContextType] = ContextType.string

    # Actor information
    actor: Optional[ContextType] = ContextType.string
    actor_id: Optional[ContextType] = ContextType.string

    # API URLs
    api_url: Optional[ContextType] = ContextType.string

    # Base reference (for PRs)
    base_ref: Optional[ContextType] = ContextType.string

    # Environment
    env: Optional[ContextType] = ContextType.string

    # Event information
    event: Optional[ContextType] = ContextType.string
    event_name: Optional[ContextType] = ContextType.string
    event_path: Optional[ContextType] = ContextType.string

    # GraphQL URL
    graphql_url: Optional[ContextType] = ContextType.string

    # Head reference (for PRs)
    head_ref: Optional[ContextType] = ContextType.string

    # Job identifier
    job: Optional[ContextType] = ContextType.string

    # Path
    path: Optional[ContextType] = ContextType.string

    # Reference information
    ref: Optional[ContextType] = ContextType.string
    ref_name: Optional[ContextType] = ContextType.string
    ref_protected: Optional[ContextType] = ContextType.string
    ref_type: Optional[ContextType] = ContextType.string

    # Repository information
    repository: Optional[ContextType] = ContextType.string
    repository_id: Optional[ContextType] = ContextType.string
    repository_owner: Optional[ContextType] = ContextType.string
    repository_owner_id: Optional[ContextType] = ContextType.string
    repositoryUrl: Optional[ContextType] = ContextType.string

    # Retention
    retention_days: Optional[ContextType] = ContextType.string

    # Run information
    run_id: Optional[ContextType] = ContextType.string
    run_number: Optional[ContextType] = ContextType.string
    run_attempt: Optional[ContextType] = ContextType.string

    # Secret source
    secret_source: Optional[ContextType] = ContextType.string

    # Server URL
    server_url: Optional[ContextType] = ContextType.string

    # SHA
    sha: Optional[ContextType] = ContextType.string

    # Token
    token: Optional[ContextType] = ContextType.string

    # Triggering actor
    triggering_actor: Optional[ContextType] = ContextType.string

    # Workflow information
    workflow: Optional[ContextType] = ContextType.string
    workflow_ref: Optional[ContextType] = ContextType.string
    workflow_sha: Optional[ContextType] = ContextType.string

    # Workspace
    workspace: Optional[ContextType] = ContextType.string


# =============================================================================
# RUNNER CONTEXT
# =============================================================================


@dataclass
class RunnerContext:
    """Runner context - contains information about the runner executing jobs.

    The runner context contains information about the runner that is executing the current job.
    """

    type_: Optional[ContextType] = ContextType.object

    # Runner name
    name: Optional[ContextType] = ContextType.string

    # Operating system
    os: Optional[ContextType] = ContextType.string

    # Architecture
    arch: Optional[ContextType] = ContextType.string

    # Temporary directory
    temp: Optional[ContextType] = ContextType.string

    # Tool cache
    tool_cache: Optional[ContextType] = ContextType.string

    # Debug mode
    debug: Optional[ContextType] = ContextType.string

    # Environment
    environment: Optional[ContextType] = ContextType.string


# =============================================================================
# SECRETS CONTEXT
# =============================================================================


@dataclass
class SecretsContext:
    """Secrets context - contains repository and organization secrets.

    The secrets context is used to access repository and organization secrets.
    """

    type_: Optional[ContextType] = ContextType.object

    # GitHub token (automatically available)
    GITHUB_TOKEN: Optional[ContextType] = ContextType.string

    # Dynamic secrets
    children_: Dict[str, ContextType] = field(default_factory=dict)


# =============================================================================
# VARS CONTEXT
# =============================================================================


@dataclass
class VarsContext:
    """Vars context - contains repository and organization variables.

    The vars context is used to access repository and organization variables.
    """

    type_: Optional[ContextType] = ContextType.object

    # Dynamic variables
    children_: Dict[str, ContextType] = field(default_factory=dict)


# =============================================================================
# JOB CONTEXT
# =============================================================================


@dataclass
class ContainerContext:
    """Container context for the current job."""

    type_: Optional[ContextType] = ContextType.object
    id: Optional[ContextType] = ContextType.string
    network: Optional[ContextType] = ContextType.string


@dataclass
class ServiceContext:
    """Service context for a specific service container."""

    type_: Optional[ContextType] = None
    network: Optional[ContextType] = ContextType.string
    ports: List[str] = field(default_factory=list)


@dataclass
class ServicesContext:
    """Services context containing all service containers."""

    type_: Optional[ContextType] = ContextType.object
    children_: Dict[str, ServiceContext] = field(default_factory=dict)


@dataclass
class JobContext:
    """Job context - contains information about the currently running job.

    The job context contains information about the currently running job.
    """

    type_: Optional[ContextType] = ContextType.object

    # Container information
    container: ContainerContext = field(default_factory=ContainerContext)

    # Services
    services: ServicesContext = field(default_factory=ServicesContext)

    # Job status
    status: Optional[ContextType] = ContextType.string


# =============================================================================
# JOBS CONTEXT
# =============================================================================


@dataclass
class OutputsContext:
    """Outputs context for job or step outputs."""

    type_: Optional[ContextType] = ContextType.object
    children_: Dict[str, ContextType] = field(default_factory=dict)


@dataclass
class JobVarContext:
    """Context for a specific job in the jobs context."""

    type_: Optional[ContextType] = None
    result: Optional[ContextType] = ContextType.string
    outputs: OutputsContext = field(default_factory=OutputsContext)


@dataclass
class JobsContext:
    """Jobs context - contains information about jobs in the workflow.

    The jobs context contains information about jobs in the current workflow run.
    """

    type_: Optional[ContextType] = ContextType.object
    children_: Dict[str, JobVarContext] = field(default_factory=dict)


# =============================================================================
# STEPS CONTEXT
# =============================================================================


@dataclass
class StepOutputsContext:
    """Outputs context for a specific step."""

    type_: Optional[ContextType] = ContextType.object
    children_: Dict[str, ContextType] = field(default_factory=dict)


@dataclass
class StepVarContext:
    """Context for a specific step in the steps context."""

    type_: Optional[ContextType] = ContextType.object
    outputs: StepOutputsContext = field(default_factory=StepOutputsContext)
    conclusion: Optional[ContextType] = ContextType.string
    outcome: Optional[ContextType] = ContextType.string


@dataclass
class StepsContext:
    """Steps context - contains information about steps in the current job.

    The steps context contains information about the steps in the current job
    that have already run.
    """

    type_: Optional[ContextType] = ContextType.object
    children_: Dict[str, StepVarContext] = field(default_factory=dict)


# =============================================================================
# STRATEGY CONTEXT
# =============================================================================


@dataclass
class StrategyContext:
    """Strategy context - contains information about the matrix execution strategy.

    The strategy context contains information about the matrix execution
    strategy for the current job.
    """

    type_: Optional[ContextType] = ContextType.object
    fail_fast: Optional[ContextType] = ContextType.boolean
    job_index: Optional[ContextType] = ContextType.number
    job_total: Optional[ContextType] = ContextType.number
    max_parallel: Optional[ContextType] = ContextType.number


# =============================================================================
# MATRIX CONTEXT
# =============================================================================


@dataclass
class MatrixContext:
    """Matrix context - contains the matrix parameters for the current job.

    The matrix context contains the matrix parameters defined in the workflow for the current job.
    """

    type_: Optional[ContextType] = ContextType.object
    children_: Dict[str, ContextType] = field(default_factory=dict)


# =============================================================================
# NEEDS CONTEXT
# =============================================================================


@dataclass
class NeedOutputsContext:
    """Outputs context for a job referenced in needs."""

    type_: Optional[ContextType] = ContextType.object
    children_: Dict[str, ContextType] = field(default_factory=dict)


@dataclass
class NeedContext:
    """Context for a specific job referenced in needs."""

    type_: Optional[ContextType] = ContextType.object
    result: Optional[ContextType] = ContextType.string
    outputs: NeedOutputsContext = field(default_factory=NeedOutputsContext)


@dataclass
class NeedsContext:
    """Needs context - contains information about jobs defined as dependencies.

    The needs context contains outputs from all jobs that are defined as
    dependencies of the current job.
    """

    type_: Optional[ContextType] = ContextType.object
    children_: Dict[str, NeedContext] = field(default_factory=dict)


# =============================================================================
# INPUTS CONTEXT
# =============================================================================


@dataclass
class InputsContext:
    """Inputs context - contains input parameters.

    The inputs context contains input properties passed to a reusable workflow,
    or to a manually triggered workflow.
    """

    type_: Optional[ContextType] = ContextType.object
    children_: Dict[str, ContextType] = field(default_factory=dict)


# =============================================================================
# BUILT-IN FUNCTIONS
# =============================================================================

# GitHub Actions expression functions with their return types
functions_ = {
    "contains()": ContextType.boolean,
    "startsWith()": ContextType.boolean,
    "endsWith()": ContextType.boolean,
    "format()": ContextType.string,
    "join()": ContextType.string,
    "toJSON()": ContextType.string,
    "fromJSON()": ContextType.object,
    "hashFiles()": ContextType.string,
    "success()": ContextType.boolean,
    "always()": ContextType.boolean,
    "cancelled()": ContextType.boolean,
    "failure()": ContextType.boolean,
}


# =============================================================================
# ROOT CONTEXTS CONTAINER
# =============================================================================


@dataclass
class Contexts:
    """Root container for all GitHub Actions contexts.

    Aggregates all available contexts following GitHub's official documentation order.
    Context availability depends on the workflow execution scope.
    """

    # Core contexts (always available)
    github: GithubContext = field(default_factory=GithubContext)
    vars: VarsContext = field(default_factory=VarsContext)
    secrets: SecretsContext = field(default_factory=SecretsContext)
    inputs: InputsContext = field(default_factory=InputsContext)

    # Job/step level contexts (conditionally available)
    runner: Optional[RunnerContext] = None
    job: Optional[JobContext] = None
    jobs: Optional[JobsContext] = None
    steps: StepsContext = field(default_factory=StepsContext)

    # Matrix/strategy contexts (matrix jobs only)
    strategy: Optional[StrategyContext] = None
    matrix: Optional[MatrixContext] = None

    # Dependency context
    needs: NeedsContext = field(default_factory=NeedsContext)

    # Built-in functions
    functions_ = functions_
