from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict


@dataclass(frozen=True)
class ContextType(Enum):
    string = auto()
    boolean = auto()
    object = auto()
    number = auto()


@dataclass(frozen=True)
class Context:
    """Defines a context node: its type, whether it's defined."""
    type_: ContextType


@dataclass
class GithubContext:
    type_: ContextType = ContextType.object
    action: Context = Context(type_=ContextType.string)
    action_path: Context = Context(type_=ContextType.string)
    action_ref: Context = Context(type_=ContextType.string)
    action_repository: Context = Context(type_=ContextType.string)
    action_status: Context = Context(type_=ContextType.string)
    actor: Context = Context(type_=ContextType.string)
    actor_id: Context = Context(type_=ContextType.string)
    api_url: Context = Context(type_=ContextType.string)
    base_ref: Context = Context(type_=ContextType.string)
    env: Context = Context(type_=ContextType.string)
    event: Context = Context(type_=ContextType.string)
    event_name: Context = Context(type_=ContextType.string)
    event_path: Context = Context(type_=ContextType.string)
    graphql_url: Context = Context(type_=ContextType.string)
    head_ref: Context = Context(type_=ContextType.string)
    job: Context = Context(type_=ContextType.string)
    path: Context = Context(type_=ContextType.string)
    ref: Context = Context(type_=ContextType.string)
    ref_name: Context = Context(type_=ContextType.string)
    ref_protected: Context = Context(type_=ContextType.string)
    ref_type: Context = Context(type_=ContextType.string)
    repository: Context = Context(type_=ContextType.string)
    repository_id: Context = Context(type_=ContextType.string)
    repository_owner: Context = Context(type_=ContextType.string)
    repository_owner_id: Context = Context(type_=ContextType.string)
    repositoryUrl: Context = Context(type_=ContextType.string)
    retention_days: Context = Context(type_=ContextType.string)
    run_id: Context = Context(type_=ContextType.string)
    run_number: Context = Context(type_=ContextType.string)
    run_attempt: Context = Context(type_=ContextType.string)
    secret_source: Context = Context(type_=ContextType.string)
    server_url: Context = Context(type_=ContextType.string)
    sha: Context = Context(type_=ContextType.string)
    token: Context = Context(type_=ContextType.string)
    triggering_actor: Context = Context(type_=ContextType.string)
    workflow: Context = Context(type_=ContextType.string)
    workflow_ref: Context = Context(type_=ContextType.string)
    workflow_sha: Context = Context(type_=ContextType.string)
    workspace: Context = Context(type_=ContextType.string)


@dataclass
class EnvContext:
    type_: ContextType = ContextType.object
    children_: Dict[str, Context] = field(default_factory=dict)


@dataclass
class VarsContext:
    type_: ContextType = ContextType.object
    children_: Dict[str, Context] = field(default_factory=dict)


@dataclass
class ContainerContext:
    type_: ContextType = ContextType.object
    id: Context = Context(type_=ContextType.string)
    network: Context = Context(type_=ContextType.string)


@dataclass
class ServiceContext:
    type_: ContextType = ContextType.object
    network: Context = Context(type_=ContextType.string)
    ports: Context = Context(type_=ContextType.string)


@dataclass
class ServicesContext:
    type_: ContextType = ContextType.object
    children_: Dict[str, ServiceContext] = field(default_factory=dict)


@dataclass
class JobContext:
    type_: ContextType = ContextType.object
    container: ContainerContext = field(default_factory=ContainerContext)
    services: ServicesContext = field(default_factory=ServicesContext)
    status: Context = Context(type_=ContextType.object)


@dataclass
class OutputsContext:
    type_: ContextType = ContextType.object
    defined_: bool = False
    children_: Dict[str, Context] = field(default_factory=dict)


@dataclass
class JobVarContext:
    type_: ContextType = ContextType.object
    defined_: bool = False
    result: Context = Context(type_=ContextType.string)
    outputs: OutputsContext = field(default_factory=OutputsContext)


@dataclass
class JobsContext:
    type_: ContextType = ContextType.object
    children_: Dict[str, JobVarContext] = field(default_factory=dict)


@dataclass
class StepOutputsContext:
    type_: ContextType = ContextType.object
    defined_: bool = False
    children_: Dict[str, Context] = field(default_factory=dict)


@dataclass
class StepVarContext:
    type_: ContextType = ContextType.object
    defined_: bool = False
    outputs: StepOutputsContext = field(default_factory=StepOutputsContext)
    conclusion: Context = Context(type_=ContextType.string)
    outcome: Context = Context(type_=ContextType.string)


@dataclass
class StepsContext:
    type_: ContextType = ContextType.object
    children_: Dict[str, StepVarContext] = field(default_factory=dict)


@dataclass
class RunnerContext:
    type_: ContextType = ContextType.object
    name: Context = Context(type_=ContextType.string)
    os: Context = Context(type_=ContextType.string)
    arch: Context = Context(type_=ContextType.string)
    temp: Context = Context(type_=ContextType.string)
    tool_cache: Context = Context(type_=ContextType.string)
    debug: Context = Context(type_=ContextType.string)
    environment: Context = Context(type_=ContextType.string)


@dataclass
class SecretsContext:
    type_: ContextType = ContextType.object
    GITHUB_TOKEN: Context = Context(type_=ContextType.string)
    children_: Dict[str, Context] = field(default_factory=dict)


@dataclass
class StrategyContext:
    type_: ContextType = ContextType.object
    fail_fast: Context = Context(type_=ContextType.string)
    job_index: Context = Context(type_=ContextType.string)
    job_total: Context = Context(type_=ContextType.string)
    max_parallel: Context = Context(type_=ContextType.string)


@dataclass
class MatrixContext:
    type_: ContextType = ContextType.object
    children_: Dict[str, Context] = field(default_factory=dict)


@dataclass
class NeedOutputsContext:
    type_: ContextType = ContextType.object
    defined_: bool = False
    children_: Dict[str, Context] = field(default_factory=dict)


@dataclass
class NeedContext:
    type_: ContextType = ContextType.object
    defined_: bool = False
    result: Context = Context(type_=ContextType.string)
    outputs: NeedOutputsContext = field(default_factory=NeedOutputsContext)


@dataclass
class NeedsContext:
    type_: ContextType = ContextType.object
    children_: Dict[str, NeedContext] = field(default_factory=dict)


@dataclass
class InputsContext:
    type_: ContextType = ContextType.object
    children_: Dict[str, Context] = field(default_factory=dict)


@dataclass
class Contexts:
    github: GithubContext = field(default_factory=GithubContext)
    env: EnvContext = field(default_factory=EnvContext)
    vars: VarsContext = field(default_factory=VarsContext)
    job: JobContext = field(default_factory=JobContext)
    jobs: JobsContext = field(default_factory=JobsContext)
    steps: StepsContext = field(default_factory=StepsContext)
    runner: RunnerContext = field(default_factory=RunnerContext)
    secrets: SecretsContext = field(default_factory=SecretsContext)
    strategy: StrategyContext = field(default_factory=StrategyContext)
    matrix: MatrixContext = field(default_factory=MatrixContext)
    needs: NeedsContext = field(default_factory=NeedsContext)
    inputs: InputsContext = field(default_factory=InputsContext)
