from abc import ABC
from dataclasses import dataclass
from typing import Optional, Dict, List


@dataclass
class Workflow:
    on_: 'On'

    jobs_: Dict[str, 'Job']

    name_: Optional[str] = None
    
    run_name_: Optional[str] = None
    
    permissions_: Optional['Permissions'] = None
    
    env_: Optional['Env'] = None
    
    defaults_: Optional['Defaults'] = None
    
    concurrency_: Optional['Concurrency'] = None

@dataclass
class On:
    tbd: None

@dataclass
class Permissions:
    tbd: None

@dataclass
class Defaults:
    tbd: None

@dataclass
class Env:
    tbd: None

@dataclass
class Defaults:
    tbd:None

@dataclass
class Concurrency:
    tbd: None

@dataclass
class Job:
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

@dataclass
class Step:
    exec: 'Exec'
    id_: Optional[str] = None
    if_: Optional[str] = None
    name_: Optional[str] = None
    env_: Optional[None] = None
    continue_on_error_: Optional[bool] = None
    timeout_minutes_: Optional[float] = None

class Exec(ABC):
    pass

@dataclass
class ExecAction(Exec):
    uses_: str
    with_: Optional[Dict[str, str]] = None
    with_args_: Optional[str] = None
    with_entrypoint_: Optional[str] = None
    
@dataclass
class ExecRun(Exec):
    run_: str
    shell_: Optional[str] = None
    working_directory_: Optional[str] = None
    
@dataclass
class Pos:
    row: int
    col: int