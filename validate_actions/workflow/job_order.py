"""
Job order analysis module for GitHub Actions workflows.

This module analyzes job dependencies, execution order, and conditions
to determine the optimal execution plan for a workflow.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

from validate_actions.pos import Pos
from validate_actions.problems import Problem, ProblemLevel
from validate_actions.workflow.ast import Job, Workflow


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


class JobOrderAnalyzer:
    """Analyzes job execution order and dependencies."""

    def analyze_workflow(self, workflow: Workflow) -> JobExecutionPlan:
        """
        Analyze a workflow and return an execution plan.

        Args:
            workflow: The workflow to analyze

        Returns:
            JobExecutionPlan containing stages and conditional jobs
        """
        jobs = list(workflow.jobs_.values())

        # Build dependency graph and extract job dependencies
        dependency_graph = self._build_dependency_graph(jobs)
        conditional_jobs = self._analyze_conditions(jobs)

        # Check for cycles
        cycles = self.detect_cycles(jobs)
        if cycles:
            # Return empty plan if there are cycles
            return JobExecutionPlan(
                stages=[], conditional_jobs=conditional_jobs, dependency_graph=dependency_graph
            )

        # Build execution stages
        stages = self._build_execution_stages(jobs, dependency_graph, conditional_jobs)

        return JobExecutionPlan(
            stages=stages, conditional_jobs=conditional_jobs, dependency_graph=dependency_graph
        )

    def detect_cycles(self, jobs: List[Job]) -> List[CyclicDependency]:
        """
        Detect circular dependencies in job graph.

        Args:
            jobs: List of jobs to analyze

        Returns:
            List of detected circular dependencies
        """
        dependency_graph = self._build_dependency_graph(jobs)
        cycles = []

        # Use DFS to detect cycles
        visited = set()
        rec_stack = set()

        def dfs(job_id: str, path: List[str]):
            if job_id in rec_stack:
                # Found a cycle - extract the cycle from path
                cycle_start = path.index(job_id)
                cycle_jobs = path[cycle_start:] + [job_id]
                cycles.append(CyclicDependency(job_ids=cycle_jobs[:-1]))  # Remove duplicate
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

    def validate_dependencies(self, jobs: List[Job]) -> List[Problem]:
        """
        Validate job dependencies for errors.

        Args:
            jobs: List of jobs to validate

        Returns:
            List of validation problems
        """
        problems = []
        job_ids = {job.job_id_ for job in jobs}
        dependency_graph = self._build_dependency_graph(jobs)

        # Check for cycles
        cycles = self.detect_cycles(jobs)
        for cycle in cycles:
            problems.append(
                Problem(
                    pos=Pos(0, 0),  # TODO: Get actual position from job
                    desc=(
                        f"Circular dependency detected: "
                        f"{' -> '.join(cycle.job_ids)} -> {cycle.job_ids[0]}"
                    ),
                    level=ProblemLevel.ERR,
                    rule="job-order-circular-dependency",
                )
            )

        # Check for self-dependencies and non-existent job references
        for job in jobs:
            dependencies = dependency_graph.get(job.job_id_, [])

            for dep in dependencies:
                # Check for self-dependency
                if dep == job.job_id_:
                    problems.append(
                        Problem(
                            pos=Pos(0, 0),  # TODO: Get actual position
                            desc=f"Job '{job.job_id_}' cannot depend on itself",
                            level=ProblemLevel.ERR,
                            rule="job-order-self-dependency",
                        )
                    )

                # Check for non-existent job reference
                if dep not in job_ids:
                    problems.append(
                        Problem(
                            pos=Pos(0, 0),  # TODO: Get actual position
                            desc=f"Job '{job.job_id_}' depends on non-existent job '{dep}'",
                            level=ProblemLevel.ERR,
                            rule="job-order-invalid-reference",
                        )
                    )

        return problems

    def get_execution_order(self, jobs: List[Job]) -> List[List[Job]]:
        """
        Get the execution order as a list of parallel stages.

        Args:
            jobs: List of jobs to order

        Returns:
            List of job lists, where each inner list represents jobs that can run in parallel
        """
        execution_plan = self.analyze_workflow(
            # Create a minimal workflow for analysis
            type("MockWorkflow", (), {"jobs_": {job.job_id_: job for job in jobs}})()
        )

        return [stage.parallel_jobs for stage in execution_plan.stages]

    def _build_dependency_graph(self, jobs: List[Job]) -> Dict[str, List[str]]:
        """Build a dependency graph from job needs."""
        graph = {}

        for job in jobs:
            dependencies = []

            # Extract dependencies from needs field
            if job.needs_ is not None:
                dependencies = [need.string for need in job.needs_]

            graph[job.job_id_] = dependencies

        return graph

    def _analyze_conditions(self, jobs: List[Job]) -> Dict[str, JobCondition]:
        """Analyze job conditions and return conditional job info."""
        conditional_jobs = {}

        for job in jobs:
            if job.if_ is not None:
                condition_expr = job.if_.string
                always_run = "always()" in condition_expr

                conditional_jobs[job.job_id_] = JobCondition(
                    expression=condition_expr, always_run=always_run
                )

        return conditional_jobs

    def _has_conditional_logic(self, job: Job) -> bool:
        """Check if job has any conditional execution logic."""
        return job.if_ is not None

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
            # Find jobs that can run now (no unmet dependencies)
            ready_jobs = []
            jobs_to_skip = []

            for job_id, job in remaining_jobs.items():
                dependencies = dependency_graph.get(job_id, [])

                # Check if job should be skipped due to conditions
                if job_id in conditional_jobs:
                    condition = conditional_jobs[job_id]
                    if self._should_skip_job(
                        condition, completed_jobs, skipped_jobs, dependencies
                    ):
                        jobs_to_skip.append(job_id)
                        continue

                # Check if job should be skipped due to skipped dependencies
                if any(dep in skipped_jobs for dep in dependencies):
                    # Job depends on a skipped job
                    if job_id not in conditional_jobs or not conditional_jobs[job_id].always_run:
                        jobs_to_skip.append(job_id)
                        continue

                # Check if all dependencies are met (either completed or skipped for always() jobs)
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

            # Mark jobs to be skipped
            for job_id in jobs_to_skip:
                skipped_jobs.add(job_id)
                remaining_jobs.pop(job_id)

                # Add implicitly skipped jobs to conditional_jobs if not already there
                if job_id not in conditional_jobs:
                    conditional_jobs[job_id] = JobCondition(
                        expression="",  # No explicit condition, skipped due to dependencies
                        always_run=False,
                    )

            if not ready_jobs and not jobs_to_skip:
                # No more jobs can run - either cycle or all remaining jobs are conditional
                break

            # Create stage with ready jobs (if any)
            if ready_jobs:
                stage = JobStage(parallel_jobs=ready_jobs[:])
                stages.append(stage)

                # Mark jobs as completed and remove from remaining
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
        # Simple static condition check
        if condition.expression == "false":
            return True

        # Check if dependencies that should succeed have completed
        for dep in condition.depends_on_success:
            if dep not in completed_jobs:
                return True

        # Always run jobs should never be skipped due to static conditions
        if condition.always_run:
            return False

        return False


# Temporary implementation to handle needs/if parsing
# This should be integrated into the jobs_builder.py when needs/if are properly implemented


def parse_job_needs(needs_value) -> List[str]:
    """Parse job needs field into list of job IDs."""
    if needs_value is None:
        return []

    if isinstance(needs_value, str):
        return [needs_value]
    elif isinstance(needs_value, list):
        return [str(need) for need in needs_value]

    return []


def parse_job_condition(if_value) -> Optional[str]:
    """Parse job if field into condition string."""
    if if_value is None:
        return None

    return str(if_value)
