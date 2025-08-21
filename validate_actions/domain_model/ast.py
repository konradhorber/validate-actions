"""Abstract Syntax Tree (AST) models for GitHub Actions workflows.

This module defines the domain model for GitHub Actions workflows, providing a structured
representation of workflow files that enables validation, analysis, and manipulation.
The AST nodes preserve position information for accurate error reporting and auto-fixing.

The AST hierarchy mirrors GitHub Actions workflow structure:
- Workflow (root) -> Jobs -> Steps -> Actions/Commands
- Events define workflow triggers
- Contexts provide runtime data access
- Permissions control repository access

All AST nodes use PyYAML token-level parsing to maintain precise position tracking.
"""

from abc import ABC
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Union

from validate_actions.domain_model import contexts
from validate_actions.domain_model.primitives import Expression, Pos, String

# =============================================================================
# CORE WORKFLOW TYPES
# =============================================================================


@dataclass
class Workflow:
    """Root AST node representing a complete GitHub Actions workflow.

    Contains all workflow-level configuration including events, jobs, and global settings.
    Each workflow maintains its own context scope for expression validation.

    Attributes:
        on_: List of events that trigger this workflow
        jobs_: Dictionary mapping job IDs to Job objects
        contexts: Available GitHub Actions contexts for expression validation
        name_: Optional display name for the workflow
        run_name_: Optional dynamic run name expression
        permissions_: Repository permissions for GITHUB_TOKEN
        env_: Global environment variables
        defaults_: Default shell and working directory settings
        concurrency_: Workflow concurrency controls
    """

    on_: List["Event"]
    jobs_: Dict["String", "Job"]
    contexts: contexts.Contexts
    name_: Optional[str] = None
    run_name_: Optional[str] = None
    permissions_: "Permissions" = field(default_factory=lambda: Permissions())
    env_: Optional["Env"] = None
    defaults_: Optional["Defaults"] = None
    concurrency_: Optional["Concurrency"] = None


# =============================================================================
# PERMISSION SYSTEM
# =============================================================================


@dataclass(frozen=True)
class Permission(Enum):
    """GitHub repository permission levels.

    Defines the access level granted to the GITHUB_TOKEN for repository operations.
    """

    none = auto()  # No access
    read = auto()  # Read-only access
    write = auto()  # Read and write access


@dataclass(frozen=True)
class Permissions:
    """Repository permissions configuration for GITHUB_TOKEN.

    Defines fine-grained permissions for different repository scopes.
    Default values are permissive to match GitHub's behavior.

    Attributes:
        actions_: Permissions for GitHub Actions
        attestations_: Permissions for attestations
        checks_: Permissions for checks API
        contents_: Permissions for repository contents
        deployments_: Permissions for deployments
        id_token_: Permissions for ID token generation
        issues_: Permissions for issues API
        metadata_: Permissions for repository metadata
        models_: Permissions for repository models (e.g. code scanning)
        discussions_: Permissions for discussions API
        packages_: Permissions for package registry
        pages_: Permissions for GitHub Pages
        pull_requests_: Permissions for pull requests API
        security_events_: Permissions for security events
        statuses_: Permissions for commit statuses
    """

    actions_: "Permission" = Permission.write
    attestations_: "Permission" = Permission.write
    checks_: "Permission" = Permission.write
    contents_: "Permission" = Permission.write
    deployments_: "Permission" = Permission.write
    id_token_: "Permission" = Permission.none
    issues_: "Permission" = Permission.write
    metadata_: "Permission" = Permission.read  # Conflicting docs: read vs write
    models_: "Permission" = Permission.none  # Conflicting docs: availability
    discussions_: "Permission" = Permission.write
    packages_: "Permission" = Permission.write
    pages_: "Permission" = Permission.write
    pull_requests_: "Permission" = Permission.write
    security_events_: "Permission" = Permission.write
    statuses_: "Permission" = Permission.write


# =============================================================================
# GLOBAL CONFIGURATION
# =============================================================================


@dataclass(frozen=True)
class Shell(Enum):
    """Supported shell types for run steps.

    Maps to GitHub Actions runner shell options.
    """

    bash = "bash"
    pwsh = "pwsh"
    python = "python"
    sh = "sh"
    cmd = "cmd"
    powershell = "powershell"


@dataclass(frozen=True)
class Defaults:
    """Default settings for run steps.

    Provides workflow-level defaults that can be overridden at job or step level.

    Attributes:
        pos: Position in source file for error reporting
        shell_: Default shell for run steps
        working_directory_: Default working directory for run steps
    """

    pos: "Pos"
    shell_: Optional["Shell"] = None
    working_directory_: Optional["String"] = None


@dataclass(frozen=True)
class Env:
    """Environment variables container with convenient access methods.

    Stores environment variables as String objects to preserve position information.
    Provides dict-like access for easy variable lookup.

    Attributes:
        variables: Dictionary mapping variable names to values
    """

    variables: Dict["String", "String"]

    def get(self, key: str) -> Optional["String"]:
        """Gets a variable value by key string if it exists."""
        string_key = String(key, Pos(0, 0))
        return self.variables.get(string_key)

    def __getitem__(self, key: str) -> "String":
        """Dictionary-like access to environment variables."""
        try:
            string_key = String(key, Pos(0, 0))
            return self.variables[string_key]
        except KeyError:
            raise KeyError(f"Environment variable '{key}' not found")

    def __contains__(self, key: str) -> bool:
        """Checks if environment contains a variable by key string."""
        return key in self.variables


@dataclass(frozen=True)
class Concurrency:
    """Workflow concurrency control configuration.

    Manages concurrent execution of workflow runs to prevent conflicts.

    Attributes:
        pos: Position in source file for error reporting
        group_: Concurrency group identifier (can be expression)
        cancel_in_progress_: Whether to cancel in-progress runs when new run starts
    """

    pos: "Pos"
    group_: "String"
    cancel_in_progress_: Optional[Union[bool, "String"]] = None


# =============================================================================
# EVENT SYSTEM
# =============================================================================


@dataclass(frozen=True, kw_only=True)
class Event:
    """Base class for all workflow trigger events.

    Events define when workflows should execute. Each event type supports
    different configuration options and filtering capabilities.

    Attributes:
        id: Event name (push, pull_request, schedule, etc.)
        types_: Optional list of event subtypes to filter on
    """

    id: "String"
    types_: Optional[List["String"]] = None


@dataclass(frozen=True, kw_only=True)
class BranchesFilterEvent(Event):
    """Event with branch filtering capabilities.

    Base for events that can be filtered by branch names using glob patterns.

    Attributes:
        branches_: List of branch patterns to include
        branches_ignore_: List of branch patterns to exclude
    """

    branches_: Optional[List["String"]] = None
    branches_ignore_: Optional[List["String"]] = None


@dataclass(frozen=True)
class PathsBranchesFilterEvent(BranchesFilterEvent):
    """Event with branch and path filtering.

    Extends branch filtering with file path pattern matching.

    Attributes:
        paths_: List of file path patterns to include
        paths_ignore_: List of file path patterns to exclude
    """

    paths_: Optional[List["String"]] = None
    paths_ignore_: Optional[List["String"]] = None


@dataclass(frozen=True)
class TagsPathsBranchesFilterEvent(PathsBranchesFilterEvent):
    """Event with comprehensive filtering options.

    Supports filtering by branches, paths, and git tags.

    Attributes:
        tags_: List of tag patterns to include
        tags_ignore_: List of tag patterns to exclude
    """

    tags_: Optional[List["String"]] = None
    tags_ignore_: Optional[List["String"]] = None


@dataclass(frozen=True)
class ScheduleEvent(Event):
    """Scheduled workflow trigger using cron syntax.

    Enables time-based workflow execution with cron expressions.

    Attributes:
        cron_: List of cron expressions defining schedule
    """

    cron_: List["String"]


# -----------------------------------------------------------------------------
# Reusable Workflow Events
# -----------------------------------------------------------------------------


@dataclass(frozen=True)
class WorkflowInput(ABC):
    """Base class for workflow input parameters.

    Defines common properties for inputs to reusable workflows.

    Attributes:
        id: Input parameter name
        description_: Human-readable description
        default_: Default value if not provided
        required_: Whether input is mandatory
    """

    id: "String"
    description_: Optional["String"] = None
    default_: Optional["String"] = None
    required_: bool = False


@dataclass(frozen=True)
class WorkflowCallEvent(Event):
    """Event for reusable workflow calls.

    Defines interface for workflows that can be called by other workflows.

    Attributes:
        inputs_: Input parameters accepted by this workflow
        outputs_: Output values provided by this workflow
        secrets_: Secret parameters required by this workflow
    """

    inputs_: Optional[List["WorkflowCallEventInput"]] = None
    outputs_: Optional[List["WorkflowCallEventOutput"]] = None
    secrets_: Optional[List["WorkflowCallEventSecret"]] = None


@dataclass(frozen=True)
class WorkflowCallInputType(Enum):
    """Supported input types for reusable workflow calls."""

    boolean = auto()
    number = auto()
    string = auto()


@dataclass(frozen=True, kw_only=True)
class WorkflowCallEventInput(WorkflowInput):
    """Typed input parameter for reusable workflows.

    Attributes:
        type_: Data type constraint for the input value
    """

    type_: "WorkflowCallInputType"


@dataclass(frozen=True)
class WorkflowCallEventOutput:
    """Output value definition for reusable workflows.

    Attributes:
        id: Output name
        value_: Expression that computes the output value
        description_: Human-readable description
    """

    id: "String"
    value_: "String"
    description_: Optional["String"] = None


@dataclass(frozen=True)
class WorkflowCallEventSecret:
    """Secret parameter for reusable workflows.

    Attributes:
        id: Secret name
        description_: Human-readable description
        required_: Whether secret must be provided
    """

    id: "String"
    description_: Optional["String"] = None
    required_: bool = False


@dataclass(frozen=True, kw_only=True)
class WorkflowRunEvent(BranchesFilterEvent):
    """Event triggered by other workflow completions.

    Attributes:
        workflows_: List of workflow names that trigger this event
    """

    workflows_: List["String"]


# -----------------------------------------------------------------------------
# Manual Workflow Dispatch
# -----------------------------------------------------------------------------


@dataclass(frozen=True)
class WorkflowDispatchEvent(Event):
    """Manual workflow trigger with optional inputs.

    Enables manual workflow execution through GitHub UI or API.

    Attributes:
        inputs_: User-configurable input parameters
    """

    inputs_: Optional[List["WorkflowDispatchEventInput"]] = None


@dataclass(frozen=True)
class WorkflowDispatchInputType(Enum):
    """Supported input types for manual workflow dispatch."""

    boolean = auto()
    number = auto()
    string = auto()
    choice = auto()  # Dropdown with predefined options
    environment = auto()  # Environment selector


@dataclass(frozen=True, kw_only=True)
class WorkflowDispatchEventInput(WorkflowInput):
    """User input for manual workflow dispatch.

    Attributes:
        type_: Input type determining UI widget
        options_: Available choices for 'choice' type inputs
    """

    type_: "WorkflowDispatchInputType"
    options_: Optional[List["String"]] = None


# =============================================================================
# JOB CONFIGURATION
# =============================================================================


@dataclass()
class RunsOn:
    """Runner selection configuration for jobs.

    Specifies which GitHub Actions runners should execute the job.
    Supports both individual labels and runner groups.

    Attributes:
        pos: Position in source file for error reporting
        labels: Individual runner labels (ubuntu-latest, windows-2022, etc.)
        group: Runner group names for organization-level runner pools
    """

    pos: "Pos"
    labels: List["String"] = field(default_factory=list)
    group: List["String"] = field(default_factory=list)


@dataclass(frozen=True)
class Strategy:
    """Job execution strategy with matrix and parallelism controls.

    Defines how jobs should be executed across different configurations.

    Attributes:
        pos: Position in source file for error reporting
        combinations: Matrix of variable combinations to execute
        fail_fast_: Whether to cancel remaining jobs on first failure
        max_parallel_: Maximum number of concurrent job instances
    """

    pos: "Pos"
    combinations: List[Dict["String", "String"]]
    fail_fast_: Optional[bool]
    max_parallel_: Optional[int]


@dataclass(frozen=True)
class Environment:
    """Deployment environment configuration.

    Links jobs to GitHub deployment environments for additional controls.

    Attributes:
        pos: Position in source file for error reporting
        name_: Environment name
        url_: Optional environment URL for deployments
    """

    pos: "Pos"
    name_: "String"
    url_: Optional["String"] = None


# =============================================================================
# CONTAINER CONFIGURATION
# =============================================================================


@dataclass(frozen=True)
class ContainerCredentials:
    """Authentication credentials for private container registries.

    Attributes:
        pos: Position in source file for error reporting
        username_: Registry username
        password_: Registry password or token
    """

    pos: "Pos"
    username_: "String"
    password_: "String"


@dataclass(frozen=True)
class Container:
    """Container configuration for job execution.

    Enables running jobs inside Docker containers for consistent environments.

    Attributes:
        pos: Position in source file for error reporting
        image_: Container image reference
        credentials_: Optional registry authentication
        env_: Container environment variables
        ports_: Port mappings between host and container
        volumes_: Volume mounts for persistent storage
        options_: Additional Docker run options
    """

    pos: "Pos"
    image_: "String"
    credentials_: Optional["ContainerCredentials"] = None
    env_: Optional["Env"] = None
    ports_: Optional[List["String"]] = None
    volumes_: Optional[List["String"]] = None
    options_: Optional["String"] = None


@dataclass(frozen=True)
class Secrets:
    """Secret configuration for reusable workflow calls.

    Manages how secrets are passed to called workflows.

    Attributes:
        pos: Position in source file for error reporting
        inherit: Whether to inherit all secrets from calling workflow
        secrets: Explicit secret mappings
    """

    pos: "Pos"
    inherit: bool = False
    secrets: Dict["String", "String"] = field(default_factory=dict)


# =============================================================================
# JOB AND STEP DEFINITIONS
# =============================================================================


@dataclass(frozen=True)
class Job:
    """Individual job within a workflow.

    Jobs are the main execution units that run on specific runners.
    They contain steps and can depend on other jobs.

    Attributes:
        pos: Position in source file for error reporting
        job_id_: Unique identifier for this job
        steps_: Ordered list of steps to execute
        contexts: Available contexts for expression validation
        name_: Human-readable job name
        permissions_: Job-level permission overrides
        needs_: List of job IDs this job depends on
        if_: Conditional expression to determine if job should run
        runs_on_: Runner selection configuration
        environment_: Deployment environment settings
        concurrency_: Job-level concurrency controls
        outputs_: Job outputs for use by dependent jobs
        env_: Job-level environment variables
        defaults_: Default settings for run steps
        timeout_minutes_: Maximum job execution time
        strategy_: Matrix execution strategy
        container_: Container to run job in
        services_: Service containers for job
        uses_: Reusable workflow reference (alternative to steps)
        with_: Inputs for reusable workflow calls
        secrets_: Secret configuration for reusable workflow calls
    """

    pos: "Pos"
    job_id_: str
    steps_: List["Step"]
    contexts: contexts.Contexts
    name_: Optional["String"] = None
    permissions_: Permissions = field(default_factory=Permissions)
    needs_: Optional[List["String"]] = None
    if_: Optional["String"] = None
    runs_on_: Optional[RunsOn] = None
    environment_: Optional[Environment] = None
    concurrency_: Optional[Concurrency] = None
    outputs_: Optional[None] = None  # TODO: Define proper output type
    env_: Optional["Env"] = None
    defaults_: Optional[Defaults] = None
    timeout_minutes_: Optional[int] = None
    strategy_: Optional[Strategy] = None
    container_: Optional["Container"] = None
    services_: Optional[None] = None  # TODO: Define proper service type
    uses_: Optional["String"] = None
    with_: Dict["String", "String"] = field(default_factory=dict)
    secrets_: Optional["Secrets"] = None


@dataclass(frozen=True)
class Step:
    """Individual step within a job.

    Steps are the atomic execution units that either run shell commands
    or invoke GitHub Actions.

    Attributes:
        pos: Position in source file for error reporting
        exec: The action or command to execute
        contexts: Available contexts for expression validation
        id_: Optional step identifier for referencing outputs
        if_: Conditional expression to determine if step should run
        name_: Human-readable step name
        env_: Step-level environment variables
        continue_on_error_: Whether job should continue if step fails
        timeout_minutes_: Maximum step execution time
    """

    pos: "Pos"
    exec: "Exec"
    contexts: contexts.Contexts
    id_: Optional["String"] = None
    if_: Optional["String"] = None
    name_: Optional["String"] = None
    env_: Optional["Env"] = None
    continue_on_error_: Optional[bool] = None
    timeout_minutes_: Optional[int] = None


# =============================================================================
# STEP EXECUTION TYPES
# =============================================================================


@dataclass
class Exec(ABC):
    """Abstract base class for step execution types.

    Steps can either run shell commands or invoke GitHub Actions.
    """

    pass


@dataclass
class ActionMetadata:
    """Metadata about a GitHub Action for validation.

    Retrieved from GitHub API or action.yml files to validate
    action usage and provide auto-completion.

    Attributes:
        required_inputs: List of mandatory input parameter names
        possible_inputs: List of all supported input parameter names
        version_tags: Available version tags for the action
        outputs: Dictionary mapping output names to descriptions
    """

    required_inputs: List[str] = field(default_factory=list)
    possible_inputs: List[str] = field(default_factory=list)
    version_tags: List[Dict] = field(default_factory=list)
    outputs: Dict[str, str] = field(default_factory=dict)


@dataclass
class ExecAction(Exec):
    """Step that executes a GitHub Action.

    Invokes reusable actions from GitHub Marketplace or repositories.

    Attributes:
        pos: Position in source file for error reporting
        uses_: Action reference (org/repo@version)
        with_: Input parameters for the action
        metadata: Optional action metadata for validation
        with_args_: Override action args (Docker actions)
        with_entrypoint_: Override action entrypoint (Docker actions)
    """

    pos: "Pos"
    uses_: "String"
    with_: Dict["String", "String"]  # Empty dict if no inputs
    metadata: Optional[ActionMetadata] = None
    with_args_: Optional["String"] = None
    with_entrypoint_: Optional["String"] = None


@dataclass
class ExecRun(Exec):
    """Step that executes shell commands.

    Runs arbitrary shell commands on the runner.

    Attributes:
        pos: Position in source file for error reporting
        run_: Shell command(s) to execute
        shell_: Shell to use for execution
        working_directory_: Directory to run commands in
    """

    pos: "Pos"
    run_: "String"
    shell_: Optional["String"] = None
    working_directory_: Optional["String"] = None

