from validate_actions.parse import parse_workflow
from typing import Dict, Any
from yaml import ScalarToken
from validate_actions.workflow_ast import *

class WorkflowFactory:
    name_ = None
    run_name_ = None
    on_ = None
    permissions_ = None
    env_ = None
    defaults_ = None
    concurrency_ = None
    jobs_ = None

    @staticmethod
    def build_workflow(token_tree: Dict[ScalarToken, Any]) -> Workflow:
        name_ = None
        run_name_ = None
        on_ = None
        permissions_ = None
        env_ = None
        defaults_ = None
        concurrency_ = None
        jobs_ = None

        for key_token in token_tree:
            key_str = key_token.value

            match key_str:
                case 'name':
                    name_ = token_tree[key_token].value
                case 'run-name':
                    run_name_ = token_tree[key_token].value
                case 'on':
                    on_ = WorkflowFactory.build_on(token_tree[key_token])
                case 'permissions':
                    permissions_ = WorkflowFactory.build_permissions(token_tree[key_token])
                case 'env':
                    env_ = WorkflowFactory.build_env(token_tree[key_token])
                case 'defaults':
                    defaults_ = WorkflowFactory.build_defaults(token_tree[key_token])
                case 'concurrency':
                    concurrency_ = WorkflowFactory.build_concurrency(token_tree[key_token])
                case 'jobs':
                    jobs_ = WorkflowFactory.build_jobs(token_tree[key_token])
                case _:
                    raise ValueError(f"Unknown key: {key_str}") #TODO
                
        return Workflow(
            on_=on_,
            jobs_=jobs_,
            name_=name_,
            run_name_=run_name_,
            permissions_=permissions_,
            env_=env_,
            defaults_=defaults_,
            concurrency_=concurrency_
        )

    @staticmethod
    def build_on(token_tree: Dict[ScalarToken, Any]) -> On:
        return On(None)
    
    @staticmethod
    def build_permissions(token_tree: Dict[ScalarToken, Any]) -> Permissions:
        return Permissions(None)
    
    @staticmethod
    def build_env(token_tree: Dict[ScalarToken, Any]) -> Env:
        return Env(None)
    
    @staticmethod
    def build_defaults(token_tree: Dict[ScalarToken, Any]) -> Defaults:
        return Defaults(None)
    
    @staticmethod
    def build_concurrency(token_tree: Dict[ScalarToken, Any]) -> Concurrency:
        return Concurrency(None)
    
    @staticmethod
    def build_jobs(jobs_token_tree: Dict[ScalarToken, Any]) -> Dict[str, Job]:
        jobs = {}
        for job_id, job_token_tree in jobs_token_tree.items():
            job_id_str = job_id.value
            jobs[job_id_str] = WorkflowFactory.build_job(job_token_tree, job_id_str)
        return jobs

    @staticmethod
    def build_job(job_token_tree: Dict[ScalarToken, Any], job_id_str: str) -> Job:
        job_id_ = job_id_str
        name_ = None
        permissions_ = None
        needs_ = None
        if_ = None
        runs_on_ = None
        environment_ = None
        concurrency_ = None
        outputs_ = None
        env_ = None
        defaults_ = None
        steps_ = []
        timeout_minutes_ = None
        strategy_ = None
        container_ = None
        services_ = None
        uses_ = None
        with_ = None
        secrets_ = None

        for key in job_token_tree:
            key_str = key.value
            match key_str:
                case 'name':
                    name_ = job_token_tree[key].value
                case 'permissions':
                    pass
                case 'needs':
                    pass
                case 'if':
                    pass
                case 'runs-on':
                    pass
                case 'environment':
                    pass
                case 'concurrency':
                    pass
                case 'outputs':
                    pass
                case 'env':
                    pass
                case 'defaults':
                    pass
                case 'steps':
                    steps_ = WorkflowFactory.build_steps(job_token_tree[key])
                case 'timeout-minutes':
                    timeout_minutes_ = job_token_tree[key].value
                case 'strategy':
                    pass
                case 'container':
                    pass
                case 'services':
                    pass
                case 'uses':
                    pass
                case 'with':
                    pass
                case 'secrets':
                    pass
                case _:
                    raise ValueError(f"Unknown job key: {key_str}")
    
        return Job(
            job_id_=job_id_,
            name_=name_,
            permissions_=permissions_,
            needs_=needs_,
            if_=if_,
            runs_on_=runs_on_,
            environment_=environment_,
            concurrency_=concurrency_,
            outputs_=outputs_,
            env_=env_,
            defaults_=defaults_,
            steps_=steps_,
            timeout_minutes_=timeout_minutes_,
            strategy_=strategy_,
            container_=container_,
            services_=services_,
            uses_=uses_,
            with_=with_,
            secrets_=secrets_
        )
    
    @staticmethod
    def build_steps(steps_token_tree: Dict[ScalarToken, Any]) -> List[Step]:
        steps = []
        for step in steps_token_tree:
            steps.append(WorkflowFactory.build_step(step))
        return steps
    
    @staticmethod
    def build_step(step_token_tree: Dict[ScalarToken, Any]) -> Step:
        id_ = None
        if_ = None
        name_ = None
        uses_ = None
        run_ = None
        working_directory_ = None
        shell_ = None
        with_ = {}
        with_args_ = None
        with_entrypoint_ = None
        env_ = None
        continue_on_error_ = None
        timeout_minutes_ = None

        # build step inputs
        for key in step_token_tree:
            key_str = key.value
            match key_str:
                case 'id':
                    id_ = step_token_tree[key].value
                case 'if':
                    if_ = step_token_tree[key].value
                case 'name':
                    name_ = step_token_tree[key].value
                case 'uses':
                    uses_ = step_token_tree[key].value
                case 'run':
                    run_ = step_token_tree[key].value
                case 'working-directory':
                    working_directory_ = step_token_tree[key].value
                case 'shell':
                    shell_ = step_token_tree[key].value
                case 'with':
                    for with_key, with_value in step_token_tree[key].items():
                        with_key_str = with_key.value
                        with_value_str = with_value.value

                        if with_key_str == 'args':
                            with_args_ = with_value_str
                        elif with_key_str == 'entrypoint':
                            with_entrypoint_ = with_value_str
                        else:
                            with_[with_key_str] = with_value_str
                case 'env':
                    pass
                case 'continue-on-error':
                    continue_on_error_ = step_token_tree[key].value
                case 'timeout-minutes':
                    timeout_minutes_ = step_token_tree[key].value
                case _:
                    raise ValueError(f"Unknown step key: {key_str}")

        exec = None
        
        # create uses xor run exec for step
        if uses_ is None and run_ is None:
            raise ValueError(f"Step must have either 'uses' or 'run' key")
        if uses_ is not None and run_ is not None:
            raise ValueError(f"Step cannot have both 'uses' and 'run' keys")
        if uses_ is not None:
            exec = ExecAction(
                uses_=uses_,
                with_=with_,
                with_args_=with_args_,
                with_entrypoint_=with_entrypoint_
            )
        else:
            exec = ExecRun(
                run_=run_,
                shell_=shell_,
                working_directory_=working_directory_
            )
        
        # create step
        return Step(
            id_=id_,
            if_=if_,
            name_=name_,
            exec=exec,
            env_=env_,
            continue_on_error_=continue_on_error_,
            timeout_minutes_=timeout_minutes_
        )