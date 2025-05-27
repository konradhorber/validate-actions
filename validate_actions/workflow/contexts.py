from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional


@dataclass(frozen=True)
class ContextType(Enum):
    string = auto()
    boolean = auto()
    object = auto()
    number = auto()


@dataclass
class GithubContext:
    type_: Optional[ContextType] = ContextType.object
    action: Optional[ContextType] = ContextType.string
    action_path: Optional[ContextType] = ContextType.string
    action_ref: Optional[ContextType] = ContextType.string
    action_repository: Optional[ContextType] = ContextType.string
    action_status: Optional[ContextType] = ContextType.string
    actor: Optional[ContextType] = ContextType.string
    actor_id: Optional[ContextType] = ContextType.string
    api_url: Optional[ContextType] = ContextType.string
    base_ref: Optional[ContextType] = ContextType.string
    env: Optional[ContextType] = ContextType.string
    event: Optional[ContextType] = ContextType.string
    event_name: Optional[ContextType] = ContextType.string
    event_path: Optional[ContextType] = ContextType.string
    graphql_url: Optional[ContextType] = ContextType.string
    head_ref: Optional[ContextType] = ContextType.string
    job: Optional[ContextType] = ContextType.string
    path: Optional[ContextType] = ContextType.string
    ref: Optional[ContextType] = ContextType.string
    ref_name: Optional[ContextType] = ContextType.string
    ref_protected: Optional[ContextType] = ContextType.string
    ref_type: Optional[ContextType] = ContextType.string
    repository: Optional[ContextType] = ContextType.string
    repository_id: Optional[ContextType] = ContextType.string
    repository_owner: Optional[ContextType] = ContextType.string
    repository_owner_id: Optional[ContextType] = ContextType.string
    repositoryUrl: Optional[ContextType] = ContextType.string
    retention_days: Optional[ContextType] = ContextType.string
    run_id: Optional[ContextType] = ContextType.string
    run_number: Optional[ContextType] = ContextType.string
    run_attempt: Optional[ContextType] = ContextType.string
    secret_source: Optional[ContextType] = ContextType.string
    server_url: Optional[ContextType] = ContextType.string
    sha: Optional[ContextType] = ContextType.string
    token: Optional[ContextType] = ContextType.string
    triggering_actor: Optional[ContextType] = ContextType.string
    workflow: Optional[ContextType] = ContextType.string
    workflow_ref: Optional[ContextType] = ContextType.string
    workflow_sha: Optional[ContextType] = ContextType.string
    workspace: Optional[ContextType] = ContextType.string


@dataclass
class EnvContext:
    type_: Optional[ContextType] = ContextType.object
    children_: Dict[str, ContextType] = field(default_factory=dict)


@dataclass
class VarsContext:
    type_: Optional[ContextType] = ContextType.object
    children_: Dict[str, ContextType] = field(default_factory=dict)


@dataclass
class ContainerContext:
    type_: Optional[ContextType] = ContextType.object
    id: Optional[ContextType] = ContextType.string
    network: Optional[ContextType] = ContextType.string


@dataclass
class ServiceContext:
    type_: Optional[ContextType] = None
    network: Optional[ContextType] = ContextType.string
    ports: List[str] = field(default_factory=list)


@dataclass
class ServicesContext:
    type_: Optional[ContextType] = ContextType.object
    children_: Dict[str, ServiceContext] = field(default_factory=dict)


@dataclass
class JobContext:
    type_: Optional[ContextType] = ContextType.object
    container: ContainerContext = field(default_factory=ContainerContext)
    services: ServicesContext = field(default_factory=ServicesContext)
    status: Optional[ContextType] = ContextType.string


@dataclass
class OutputsContext:
    type_: Optional[ContextType] = ContextType.object
    children_: Dict[str, ContextType] = field(default_factory=dict)


@dataclass
class JobVarContext:
    type_: Optional[ContextType] = None
    result: Optional[ContextType] = ContextType.string
    outputs: OutputsContext = field(default_factory=OutputsContext)


@dataclass
class JobsContext:
    type_: Optional[ContextType] = ContextType.object
    children_: Dict[str, JobVarContext] = field(default_factory=dict)


@dataclass
class StepOutputsContext:
    type_: Optional[ContextType] = ContextType.object
    children_: Dict[str, ContextType] = field(default_factory=dict)


@dataclass
class StepVarContext:
    type_: Optional[ContextType] = ContextType.object
    outputs: StepOutputsContext = field(default_factory=StepOutputsContext)
    conclusion: Optional[ContextType] = ContextType.string
    outcome: Optional[ContextType] = ContextType.string


@dataclass
class StepsContext:
    type_: Optional[ContextType] = ContextType.object
    children_: Dict[str, StepVarContext] = field(default_factory=dict)


@dataclass
class RunnerContext:
    type_: Optional[ContextType] = ContextType.object
    name: Optional[ContextType] = ContextType.string
    os: Optional[ContextType] = ContextType.string
    arch: Optional[ContextType] = ContextType.string
    temp: Optional[ContextType] = ContextType.string
    tool_cache: Optional[ContextType] = ContextType.string
    debug: Optional[ContextType] = ContextType.string
    environment: Optional[ContextType] = ContextType.string


@dataclass
class SecretsContext:
    type_: Optional[ContextType] = ContextType.object
    GITHUB_TOKEN: Optional[ContextType] = ContextType.string
    children_: Dict[str, ContextType] = field(default_factory=dict)


@dataclass
class StrategyContext:
    type_: Optional[ContextType] = ContextType.object
    fail_fast: Optional[ContextType] = ContextType.string
    job_index: Optional[ContextType] = ContextType.string
    job_total: Optional[ContextType] = ContextType.string
    max_parallel: Optional[ContextType] = ContextType.string


@dataclass
class MatrixContext:
    type_: Optional[ContextType] = ContextType.object
    children_: Dict[str, ContextType] = field(default_factory=dict)


@dataclass
class NeedOutputsContext:
    type_: Optional[ContextType] = ContextType.object
    children_: Dict[str, ContextType] = field(default_factory=dict)


@dataclass
class NeedContext:
    type_: Optional[ContextType] = ContextType.object
    result: Optional[ContextType] = ContextType.string
    outputs: NeedOutputsContext = field(default_factory=NeedOutputsContext)


@dataclass
class NeedsContext:
    type_: Optional[ContextType] = ContextType.object
    children_: Dict[str, NeedContext] = field(default_factory=dict)


@dataclass
class InputsContext:
    type_: Optional[ContextType] = ContextType.object
    children_: Dict[str, ContextType] = field(default_factory=dict)


functions_ = {
    'contains()': ContextType.boolean,
    'startsWith()': ContextType.boolean,
    'endsWith()': ContextType.boolean,
    'format()': ContextType.string,
    'join()': ContextType.string,
    'toJSON()': ContextType.string,
    'fromJSON()': ContextType.object,
    'hashFiles()': ContextType.string,
    'success()': ContextType.boolean,
    'always()': ContextType.boolean,
    'cancelled()': ContextType.boolean,
    'failure()': ContextType.boolean,
}


@dataclass
class Contexts:
    github: GithubContext = field(default_factory=GithubContext)
    env: EnvContext = field(default_factory=EnvContext)
    vars: VarsContext = field(default_factory=VarsContext)
    job: Optional[JobContext] = None
    jobs: JobsContext = field(default_factory=JobsContext)
    steps: StepsContext = field(default_factory=StepsContext)
    runner: Optional[RunnerContext] = None
    secrets: SecretsContext = field(default_factory=SecretsContext)
    strategy: StrategyContext = field(default_factory=StrategyContext)
    matrix: MatrixContext = field(default_factory=MatrixContext)
    needs: NeedsContext = field(default_factory=NeedsContext)
    inputs: InputsContext = field(default_factory=InputsContext)
    functions_ = functions_
