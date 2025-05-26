from abc import ABC
from dataclasses import dataclass
from enum import Enum, auto
from typing import Dict, List, Optional

from yaml import ScalarToken

from validate_actions.pos import Pos


@dataclass(frozen=True)
class Permission(Enum):
    none = auto()
    read = auto()
    write = auto()


# TODO solution for default values, currently using default permissive
@dataclass(frozen=True)
class Permissions:
    actions_: "Permission" = Permission.write
    attestations_: "Permission" = Permission.write
    checks_: "Permission" = Permission.write
    contents_: "Permission" = Permission.write
    deployments_: "Permission" = Permission.write
    id_token_: "Permission" = Permission.none
    issues_: "Permission" = Permission.write
    metadata_: "Permission" = Permission.read  # TODO conflicting docs
    models_: "Permission" = Permission.none  # TODO conflicting docs
    discussions_: "Permission" = Permission.write
    packages_: "Permission" = Permission.write
    pages_: "Permission" = Permission.write
    pull_requests_: "Permission" = Permission.write
    security_events_: "Permission" = Permission.write
    statuses_: "Permission" = Permission.write


@dataclass(frozen=True)
class Workflow:
    on_: List["Event"]
    jobs_: Dict["String", "Job"]
    name_: Optional[str] = None
    run_name_: Optional[str] = None
    permissions_: "Permissions" = Permissions()
    env_: Optional["Env"] = None
    defaults_: Optional["Defaults"] = None
    concurrency_: Optional["Concurrency"] = None
    contexts: Optional[Dict['str', 'Context']] = None


# region On
@dataclass(frozen=True, kw_only=True)
class Event:
    id: "String"
    types_: Optional[List["String"]] = None


@dataclass(frozen=True, kw_only=True)
class BranchesFilterEvent(Event):
    branches_: Optional[List["String"]] = None
    branches_ignore_: Optional[List["String"]] = None


@dataclass(frozen=True)
class PathsBranchesFilterEvent(BranchesFilterEvent):
    paths_: Optional[List["String"]] = None
    paths_ignore_: Optional[List["String"]] = None


@dataclass(frozen=True)
class TagsPathsBranchesFilterEvent(PathsBranchesFilterEvent):
    tags_: Optional[List["String"]] = None
    tags_ignore_: Optional[List["String"]] = None


@dataclass(frozen=True)
class ScheduleEvent(Event):
    cron_: List["String"]


@dataclass(frozen=True)
class WorkflowCallEvent(Event):
    inputs_: Optional[List["WorkflowCallEventInput"]] = None
    outputs_: Optional[List["WorkflowCallEventOutput"]] = None
    secrets_: Optional[List["WorkflowCallEventSecret"]] = None


@dataclass(frozen=True)
class WorkflowInput(ABC):
    id: "String"
    description_: Optional["String"] = None
    default_: Optional["String"] = None
    required_: bool = False


@dataclass(frozen=True, kw_only=True)
class WorkflowCallEventInput(WorkflowInput):
    type_: "WorkflowCallInputType"


@dataclass(frozen=True)
class WorkflowCallInputType(Enum):
    boolean = auto()
    number = auto()
    string = auto()


@dataclass(frozen=True)
class WorkflowCallEventOutput:
    id: "String"
    value_: "String"
    description_: Optional["String"] = None


@dataclass(frozen=True)
class WorkflowCallEventSecret:
    id: "String"
    description_: Optional["String"] = None
    required_: bool = False


@dataclass(frozen=True, kw_only=True)
class WorkflowRunEvent(BranchesFilterEvent):
    workflows_: List["String"]


@dataclass(frozen=True)
class WorkflowDispatchEvent(Event):
    inputs_: Optional[List["WorkflowDispatchEventInput"]] = None


@dataclass(frozen=True, kw_only=True)
class WorkflowDispatchEventInput(WorkflowInput):
    type_: "WorkflowDispatchInputType"
    options_: Optional[List["String"]] = None


@dataclass(frozen=True)
class WorkflowDispatchInputType(Enum):
    boolean = auto()
    number = auto()
    string = auto()
    choice = auto()
    environment = auto()


# endregion On


@dataclass(frozen=True)
class Defaults:
    tbd: None


@dataclass(frozen=True)
class Env:
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
    tbd: None


# region Jobs
@dataclass(frozen=True)
class Job:
    pos: "Pos"
    job_id_: str
    steps_: List["Step"]
    name_: Optional["String"] = None
    permissions_: Permissions = Permissions()
    needs_: Optional[None] = None
    if_: Optional[None] = None
    runs_on_: Optional[None] = None
    environment_: Optional[None] = None
    concurrency_: Optional[None] = None
    outputs_: Optional[None] = None
    env_: Optional["Env"] = None
    defaults_: Optional[None] = None
    timeout_minutes_: Optional[int] = None
    strategy_: Optional[None] = None
    container_: Optional[None] = None
    services_: Optional[None] = None
    uses_: Optional[None] = None
    with_: Optional[None] = None
    secrets_: Optional[None] = None


@dataclass(frozen=True)
class Step:
    pos: "Pos"
    exec: "Exec"
    id_: Optional["String"] = None
    if_: Optional["String"] = None
    name_: Optional["String"] = None
    env_: Optional["Env"] = None
    continue_on_error_: Optional[bool] = None
    timeout_minutes_: Optional[int] = None


@dataclass(frozen=True)
class Exec(ABC):
    pass


@dataclass(frozen=True)
class ExecAction(Exec):
    pos: "Pos"
    uses_: "String"
    # empty dict if no inputs
    with_: Dict["String", "String"]
    with_args_: Optional["String"] = None
    with_entrypoint_: Optional["String"] = None


@dataclass(frozen=True)
class ExecRun(Exec):
    pos: "Pos"
    run_: "String"
    shell_: Optional["String"] = None
    working_directory_: Optional["String"] = None


# endregion Jobs


@dataclass(frozen=True)
class String:
    """Represents a string value along with its positional metadata."""

    string: str
    """The string value extracted from the token."""
    pos: "Pos"
    """The position of the string in the source, including line and column."""

    @classmethod
    def from_token(cls, token: ScalarToken) -> "String":
        """Creates a String instance from a PyYAML ScalarToken."""
        return cls(token.value, Pos.from_token(token))

    def __eq__(self, other):
        """Compare only based on string content."""
        if isinstance(other, String):
            return self.string == other.string
        elif isinstance(other, str):
            return self.string == other
        return NotImplemented

    def __hash__(self):
        """Hash only based on string content."""
        return hash(self.string)


@dataclass(frozen=True)
class Reference(String):
    pos: "Pos"
    string: str
    parts: List[str]


@dataclass(frozen=True)
class Context:
    """Defines a context node: its type, whether it's defined, and optional children."""

    type_: str  # one of 'string', 'boolean', 'object', 'number'
    defined_: bool
    children_: Optional[Dict[str, "Context"]] = None
