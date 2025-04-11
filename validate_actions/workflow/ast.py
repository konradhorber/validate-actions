from abc import ABC
from dataclasses import dataclass
from typing import Optional, Dict, List
from enum import Enum, auto
from yaml import ScalarToken, Token


@dataclass(frozen=True)
class Workflow:
    on_: List['Event']
    jobs_: Dict['String', 'Job']
    name_: Optional[str] = None
    run_name_: Optional[str] = None
    permissions_: Optional['Permissions'] = None
    env_: Optional['Env'] = None
    defaults_: Optional['Defaults'] = None
    concurrency_: Optional['Concurrency'] = None


# region On
@dataclass(frozen=True, kw_only=True)
class Event():
    id: 'String'
    types_: Optional[List['String']] = None


@dataclass(frozen=True, kw_only=True)
class BranchesFilterEvent(Event):
    branches_: Optional[List['String']] = None
    branches_ignore_: Optional[List['String']] = None


@dataclass(frozen=True)
class PathsBranchesFilterEvent(BranchesFilterEvent):
    paths_: Optional[List['String']] = None
    paths_ignore_: Optional[List['String']] = None


@dataclass(frozen=True)
class TagsPathsBranchesFilterEvent(PathsBranchesFilterEvent):
    tags_: Optional[List['String']] = None
    tags_ignore_: Optional[List['String']] = None


@dataclass(frozen=True)
class ScheduleEvent(Event):
    cron_: List['String']


@dataclass(frozen=True)
class WorkflowCallEvent(Event):
    inputs_: Optional[List['WorkflowCallEventInput']] = None
    outputs_: Optional[List['WorkflowCallEventOutput']] = None
    secrets_: Optional[List['WorkflowCallEventSecret']] = None


@dataclass(frozen=True)
class WorkflowInput(ABC):
    id: 'String'
    description_: Optional['String'] = None
    default_: Optional['String'] = None
    required_: bool = False


@dataclass(frozen=True, kw_only=True)
class WorkflowCallEventInput(WorkflowInput):
    type_: 'WorkflowCallInputType'


@dataclass(frozen=True)
class WorkflowCallInputType(Enum):
    boolean = auto()
    number = auto()
    string = auto()


@dataclass(frozen=True)
class WorkflowCallEventOutput():
    id: 'String'
    value_: 'String'
    description_: Optional['String'] = None


@dataclass(frozen=True)
class WorkflowCallEventSecret():
    id: 'String'
    description_: Optional['String'] = None
    required_: bool = False


@dataclass(frozen=True, kw_only=True)
class WorkflowRunEvent(BranchesFilterEvent):
    workflows_: List['String']


@dataclass(frozen=True)
class WorkflowDispatchEvent(Event):
    inputs_: Optional[List['WorkflowDispatchEventInput']] = None


@dataclass(frozen=True, kw_only=True)
class WorkflowDispatchEventInput(WorkflowInput):
    type_: 'WorkflowDispatchInputType'
    options_: Optional[List['String']] = None


@dataclass(frozen=True)
class WorkflowDispatchInputType(Enum):
    boolean = auto()
    number = auto()
    string = auto()
    choice = auto()
    environment = auto()
# endregion On


@dataclass(frozen=True)
class Permissions:
    tbd: None


@dataclass(frozen=True)
class Defaults:
    tbd: None


@dataclass(frozen=True)
class Env:
    tbd: None


@dataclass(frozen=True)
class Concurrency:
    tbd: None


# region Jobs
@dataclass(frozen=True)
class Job:
    pos: 'Pos'
    job_id_: str
    steps_: List['Step']
    name_: Optional[str] = None
    permissions_: Optional[None] = None
    needs_: Optional[None] = None
    if_: Optional[None] = None
    runs_on_: Optional[None] = None
    environment_: Optional[None] = None
    concurrency_: Optional[None] = None
    outputs_: Optional[None] = None
    env_: Optional[None] = None
    defaults_: Optional[None] = None
    timeout_minutes_: Optional[float] = None
    strategy_: Optional[None] = None
    container_: Optional[None] = None
    services_: Optional[None] = None
    uses_: Optional[None] = None
    with_: Optional[None] = None
    secrets_: Optional[None] = None


@dataclass(frozen=True)
class Step:
    pos: 'Pos'
    exec: 'Exec'
    id_: Optional[str] = None
    if_: Optional[str] = None
    name_: Optional[str] = None
    env_: Optional[None] = None
    continue_on_error_: Optional[bool] = None
    timeout_minutes_: Optional[float] = None


@dataclass(frozen=True)
class Exec(ABC):
    pass


@dataclass(frozen=True)
class ExecAction(Exec):
    pos: 'Pos'
    uses_: str
    # empty dict if no inputs
    with_: Dict[str, str]
    with_args_: Optional[str] = None
    with_entrypoint_: Optional[str] = None


@dataclass(frozen=True)
class ExecRun(Exec):
    pos: 'Pos'
    run_: str
    shell_: Optional[str] = None
    working_directory_: Optional[str] = None
# endregion Jobs


@dataclass(frozen=True)
class Pos:
    line: int
    col: int

    @classmethod
    def from_token(cls, token: Token) -> 'Pos':
        """Creates a Pos instance from a YAML token."""
        return cls(token.start_mark.line, token.start_mark.column)


@dataclass(frozen=True)
class String:
    """Represents a string value along with its positional metadata."""
    string: str
    """The string value extracted from the token."""
    pos: 'Pos'
    """The position of the string in the source, including line and column."""

    @classmethod
    def from_token(cls, token: ScalarToken) -> 'String':
        """Creates a String instance from a PyYAML ScalarToken.
        """
        return cls(token.value, Pos.from_token(token))
