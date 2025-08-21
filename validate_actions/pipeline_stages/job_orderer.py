"""
Job ordering module for GitHub Actions workflows.

This module provides implementations for analyzing job dependencies,
execution order, and conditions to determine the optimal execution plan for a workflow.
"""

from abc import abstractmethod
from typing import Dict, List, Optional, Set

import validate_actions.domain_model.ast as ast
from validate_actions.domain_model.ast import Job, Workflow
from validate_actions.domain_model.contexts import (
    ContextType,
    NeedContext,
    NeedOutputsContext,
    NeedsContext,
)
from validate_actions.domain_model.job_order_models import (
    CyclicDependency,
    JobCondition,
    JobExecutionPlan,
    JobStage,
)
from validate_actions.globals.problems import Problem, ProblemLevel, Problems
from validate_actions.globals.process_stage import ProcessStage


class JobOrderer(ProcessStage[ast.Workflow, ast.Workflow]):
    """Interface for job ordering and dependency analysis."""

    @abstractmethod
    def process(self, workflow: ast.Workflow) -> ast.Workflow:
        """Process workflow with job dependency analysis and needs contexts.

        Args:
            workflow: The workflow to analyze and enrich with job ordering

        Returns:
            ast.Workflow: The workflow with job dependency analysis completed
        """
        pass


class DefaultJobOrderer(JobOrderer):
    """Analyzes and prepares workflows with proper job dependency analysis and needs contexts."""

    def __init__(self, problems: Problems) -> None:
        self.problems = problems
        self.RULE_NAME = "job-order"

    def process(self, workflow: ast.Workflow) -> Workflow:
        """Process workflow with job dependency analysis and needs contexts."""
        execution_plan = self._analyze_workflow(workflow)
        self._populate_needs_contexts(workflow, execution_plan)
        return workflow

    def _analyze_workflow(self, workflow: Workflow) -> JobExecutionPlan:
        """Analyze a workflow and return an execution plan."""
        jobs = list(workflow.jobs_.values())

        dependency_graph = self._build_dependency_graph(jobs)
        self._validate_job_dependencies(jobs, dependency_graph)
        conditional_jobs = self._analyze_conditions(jobs)

        cycles = self._detect_cycles(jobs, dependency_graph)
        if cycles:
            return JobExecutionPlan(
                stages=[], conditional_jobs=conditional_jobs, dependency_graph=dependency_graph
            )

        stages = self._build_execution_stages(jobs, dependency_graph, conditional_jobs)

        return JobExecutionPlan(
            stages=stages, conditional_jobs=conditional_jobs, dependency_graph=dependency_graph
        )

    def _build_dependency_graph(self, jobs: List[Job]) -> Dict[str, List[str]]:
        """Build a dependency graph from job needs."""
        graph = {}
        for job in jobs:
            dependencies = []
            if job.needs_ is not None:
                for need in job.needs_:
                    dependencies.append(need.string)
            graph[job.job_id_] = dependencies
        return graph

    def _validate_job_dependencies(
        self, jobs: List[Job], dependency_graph: Dict[str, List[str]]
    ) -> None:
        """Validate job dependency references."""
        job_ids = {job.job_id_ for job in jobs}

        for job in jobs:
            if job.needs_ is not None:
                for need in job.needs_:
                    dep_id = need.string

                    if dep_id == job.job_id_:
                        self.problems.append(
                            Problem(
                                pos=need.pos,
                                desc=f"Job '{job.job_id_}' cannot depend on itself",
                                level=ProblemLevel.ERR,
                                rule=self.RULE_NAME,
                            )
                        )
                    elif dep_id not in job_ids:
                        self.problems.append(
                            Problem(
                                pos=need.pos,
                                desc=f"Job '{job.job_id_}' depends on non-existent job '{dep_id}'",
                                level=ProblemLevel.ERR,
                                rule=self.RULE_NAME,
                            )
                        )

    def _analyze_conditions(self, jobs: List[Job]) -> Dict[str, JobCondition]:
        """Analyze job conditions and return conditional job info."""
        conditional_jobs = {}
        for job in jobs:
            if job.if_ is not None:
                condition_expr = job.if_.string
                always_run = "always()" in condition_expr
                if condition_expr == "false":
                    self.problems.append(
                        Problem(
                            pos=job.if_.pos,
                            desc=f"Job '{job.job_id_}' never runs due to condition 'false'",
                            level=ProblemLevel.WAR,
                            rule=self.RULE_NAME,
                        )
                    )
                conditional_jobs[job.job_id_] = JobCondition(
                    expression=condition_expr, always_run=always_run
                )
        return conditional_jobs

    def _detect_cycles(
        self, jobs: List[Job], dependency_graph: Dict[str, List[str]]
    ) -> List[CyclicDependency]:
        """Detect circular dependencies in job graph and add problems."""
        cycles = []
        visited: Set[str] = set()
        rec_stack: Set[str] = set()

        def dfs(job_id: str, path: List[str]):
            if job_id in rec_stack:
                cycle_start = path.index(job_id)
                cycle_jobs = path[cycle_start:] + [job_id]
                cycle = CyclicDependency(job_ids=cycle_jobs[:-1])
                cycles.append(cycle)

                job = next(j for j in jobs if j.job_id_ == job_id)
                self.problems.append(
                    Problem(
                        pos=job.pos,
                        desc=(
                            f"Circular dependency detected: "
                            f"{' -> '.join(cycle.job_ids)} -> {cycle.job_ids[0]}"
                        ),
                        level=ProblemLevel.ERR,
                        rule=self.RULE_NAME,
                    )
                )
                return

            if job_id in visited:
                return

            visited.add(job_id)
            rec_stack.add(job_id)
            path.append(job_id)

            for dep in dependency_graph.get(job_id, []):
                dfs(dep, path)

            path.pop()
            rec_stack.remove(job_id)

        for job in jobs:
            if job.job_id_ not in visited:
                dfs(job.job_id_, [])

        return cycles

    def _build_execution_stages(
        self,
        jobs: List[Job],
        dependency_graph: Dict[str, List[str]],
        conditional_jobs: Dict[str, JobCondition],
    ) -> List[JobStage]:
        """Build execution stages from dependency graph."""
        stages = []
        remaining_jobs = {job.job_id_: job for job in jobs}
        completed_jobs: Set[str] = set()
        skipped_jobs: Set[str] = set()

        while remaining_jobs:
            ready_jobs = []
            jobs_to_skip = []

            for job_id, job in remaining_jobs.items():
                dependencies = dependency_graph.get(job_id, [])

                if job_id in conditional_jobs:
                    condition = conditional_jobs[job_id]
                    if self._should_skip_job(
                        condition, completed_jobs, skipped_jobs, dependencies
                    ):
                        jobs_to_skip.append(job_id)
                        continue

                if any(dep in skipped_jobs for dep in dependencies):
                    if job_id not in conditional_jobs or not conditional_jobs[job_id].always_run:
                        jobs_to_skip.append(job_id)
                        continue

                deps_satisfied = True
                for dep in dependencies:
                    if dep not in completed_jobs:
                        if dep not in skipped_jobs or (
                            job_id not in conditional_jobs
                            or not conditional_jobs[job_id].always_run
                        ):
                            deps_satisfied = False
                            break

                if deps_satisfied:
                    ready_jobs.append(job)

            for job_id in jobs_to_skip:
                skipped_jobs.add(job_id)
                remaining_jobs.pop(job_id)

                if job_id not in conditional_jobs:
                    conditional_jobs[job_id] = JobCondition(expression="", always_run=False)

            if not ready_jobs and not jobs_to_skip:
                break

            if ready_jobs:
                stage = JobStage(parallel_jobs=ready_jobs[:])
                stages.append(stage)

                for job in ready_jobs:
                    completed_jobs.add(job.job_id_)
                    remaining_jobs.pop(job.job_id_)

        return stages

    def _should_skip_job(
        self,
        condition: JobCondition,
        completed_jobs: Set[str],
        skipped_jobs: Set[str],
        dependencies: List[str],
    ) -> bool:
        """Determine if a job should be skipped based on its condition."""
        if condition.expression == "false":
            return True

        for dep in condition.depends_on_success:
            if dep not in completed_jobs:
                return True

        if condition.always_run:
            return False

        return False

    def _populate_needs_contexts(
        self, workflow: ast.Workflow, execution_plan: JobExecutionPlan
    ) -> None:
        """Populate each job's needs context based on execution plan dependencies."""
        for job_id, job in workflow.jobs_.items():
            dependencies = execution_plan.dependency_graph.get(job_id.string, [])

            if dependencies:
                needs_context = NeedsContext()
                for dep_job_id in dependencies:
                    job_strings = [j.string for j in workflow.jobs_.keys()]
                    if dep_job_id in job_strings:
                        need_context = NeedContext(
                            type_=ContextType.object,
                            result=ContextType.string,
                            outputs=self._build_needs_outputs_context(dep_job_id, workflow),
                        )
                        needs_context.children_[dep_job_id] = need_context

                job.contexts.needs = needs_context
                for step in job.steps_:
                    step.contexts.needs = needs_context
            else:
                job.contexts.needs = NeedsContext()
                for step in job.steps_:
                    step.contexts.needs = NeedsContext()

    def _build_needs_outputs_context(
        self, job_id: str, workflow: ast.Workflow
    ) -> NeedOutputsContext:
        """Build outputs context for a needed job by looking up its JobVarContext."""
        if workflow.contexts.jobs and workflow.contexts.jobs.children_:
            job_var_context = workflow.contexts.jobs.children_.get(job_id)
            if job_var_context and job_var_context.outputs:
                outputs_context = NeedOutputsContext()
                outputs_context.children_ = job_var_context.outputs.children_
                return outputs_context

        return NeedOutputsContext()

    def _parse_job_needs(self, needs_value) -> List[str]:
        """Parse job needs field into list of job IDs."""
        if needs_value is None:
            return []
        if isinstance(needs_value, str):
            return [needs_value]
        elif isinstance(needs_value, list):
            return [str(need) for need in needs_value]
        return []

    def _parse_job_condition(self, if_value) -> Optional[str]:
        """Parse job if field into condition string."""
        if if_value is None:
            return None
        return str(if_value)
