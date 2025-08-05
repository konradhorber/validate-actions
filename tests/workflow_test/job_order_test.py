# flake8: noqa: E501

import pytest

from tests.helper import parse_workflow_string
from validate_actions.core.problems import ProblemLevel, Problems
from validate_actions.order.job_orderer import (
    CyclicDependency,
    JobExecutionPlan,
    JobOrderer,
    JobStage,
)


class TestJobOrderBasicDependencies:
    """Test basic job dependency scenarios."""

    def test_no_dependencies_parallel_execution(self):
        """Jobs with no dependencies should run in parallel."""
        workflow_string = """
        name: 'Test Parallel Jobs'
        on: push
        jobs:
          job1:
            runs-on: ubuntu-latest
            steps:
              - run: echo "job1"
          job2:
            runs-on: ubuntu-latest
            steps:
              - run: echo "job2"
          job3:
            runs-on: ubuntu-latest
            steps:
              - run: echo "job3"
        """
        workflow, problems = parse_workflow_string(workflow_string)
        analyzer = JobOrderer(Problems())
        execution_plan = analyzer._analyze_workflow(workflow)
        
        # All jobs should be in the first stage (parallel execution)
        assert len(execution_plan.stages) == 1
        assert len(execution_plan.stages[0].parallel_jobs) == 3
        job_names = {job.job_id_ for job in execution_plan.stages[0].parallel_jobs}
        assert job_names == {"job1", "job2", "job3"}

    def test_single_dependency_sequential_execution(self):
        """Job with single dependency should wait for dependency to complete."""
        workflow_string = """
        name: 'Test Single Dependency'
        on: push
        jobs:
          build:
            runs-on: ubuntu-latest
            steps:
              - run: echo "building"
          test:
            needs: build
            runs-on: ubuntu-latest
            steps:
              - run: echo "testing"
        """
        workflow, problems = parse_workflow_string(workflow_string)
        analyzer = JobOrderer(Problems())
        execution_plan = analyzer._analyze_workflow(workflow)
        
        # Should have 2 stages: build first, then test
        assert len(execution_plan.stages) == 2
        assert len(execution_plan.stages[0].parallel_jobs) == 1
        assert execution_plan.stages[0].parallel_jobs[0].job_id_ == "build"
        assert len(execution_plan.stages[1].parallel_jobs) == 1
        assert execution_plan.stages[1].parallel_jobs[0].job_id_ == "test"

    def test_multiple_dependencies_wait_for_all(self):
        """Job with multiple dependencies should wait for ALL to complete."""
        workflow_string = """
        name: 'Test Multiple Dependencies'
        on: push
        jobs:
          build:
            runs-on: ubuntu-latest
            steps:
              - run: echo "building"
          lint:
            runs-on: ubuntu-latest
            steps:
              - run: echo "linting"
          test:
            needs: [build, lint]
            runs-on: ubuntu-latest
            steps:
              - run: echo "testing"
        """
        workflow, problems = parse_workflow_string(workflow_string)
        analyzer = JobOrderer(Problems())
        execution_plan = analyzer._analyze_workflow(workflow)
        
        # Should have 2 stages: build+lint parallel, then test
        assert len(execution_plan.stages) == 2
        assert len(execution_plan.stages[0].parallel_jobs) == 2
        stage1_jobs = {job.job_id_ for job in execution_plan.stages[0].parallel_jobs}
        assert stage1_jobs == {"build", "lint"}
        assert len(execution_plan.stages[1].parallel_jobs) == 1
        assert execution_plan.stages[1].parallel_jobs[0].job_id_ == "test"

    def test_dependency_chain_linear_execution(self):
        """Jobs in a dependency chain should execute linearly."""
        workflow_string = """
        name: 'Test Dependency Chain'
        on: push
        jobs:
          build:
            runs-on: ubuntu-latest
            steps:
              - run: echo "building"
          test:
            needs: build
            runs-on: ubuntu-latest
            steps:
              - run: echo "testing"
          deploy:
            needs: test
            runs-on: ubuntu-latest
            steps:
              - run: echo "deploying"
        """
        workflow, problems = parse_workflow_string(workflow_string)
        analyzer = JobOrderer(Problems())
        execution_plan = analyzer._analyze_workflow(workflow)
        
        # Should have 3 stages: build -> test -> deploy
        assert len(execution_plan.stages) == 3
        assert execution_plan.stages[0].parallel_jobs[0].job_id_ == "build"
        assert execution_plan.stages[1].parallel_jobs[0].job_id_ == "test"
        assert execution_plan.stages[2].parallel_jobs[0].job_id_ == "deploy"


class TestJobOrderConditionalExecution:
    """Test job conditional execution scenarios."""

    def test_static_false_condition_skips_job(self):
        """Job with static false condition should be skipped."""
        workflow_string = """
        name: 'Test Static False Condition'
        on: push
        jobs:
          job1:
            if: false
            runs-on: ubuntu-latest
            steps:
              - run: echo "job1"
          job2:
            runs-on: ubuntu-latest
            steps:
              - run: echo "job2"
        """
        workflow, problems = parse_workflow_string(workflow_string)
        analyzer = JobOrderer(Problems())
        execution_plan = analyzer._analyze_workflow(workflow)
        
        # Only job2 should be in execution plan
        assert len(execution_plan.stages) == 1
        assert len(execution_plan.stages[0].parallel_jobs) == 1
        assert execution_plan.stages[0].parallel_jobs[0].job_id_ == "job2"
        
        # job1 should be marked as conditionally skipped
        assert "job1" in execution_plan.conditional_jobs
        assert execution_plan.conditional_jobs["job1"].always_run == False

    def test_dependency_on_skipped_job_also_skipped(self):
        """Job depending on skipped job should also be skipped."""
        workflow_string = """
        name: 'Test Dependency on Skipped Job'
        on: push
        jobs:
          job1:
            if: false
            runs-on: ubuntu-latest
            steps:
              - run: echo "job1"
          job2:
            needs: job1
            runs-on: ubuntu-latest
            steps:
              - run: echo "job2"
        """
        workflow, problems = parse_workflow_string(workflow_string)
        analyzer = JobOrderer(Problems())
        execution_plan = analyzer._analyze_workflow(workflow)
        
        # No jobs should execute
        assert len(execution_plan.stages) == 0
        
        # Both jobs should be marked as skipped
        assert "job1" in execution_plan.conditional_jobs
        assert "job2" in execution_plan.conditional_jobs

    def test_always_run_despite_failed_dependency(self):
        """Job with always() condition should run despite dependency failure."""
        workflow_string = """
        name: 'Test Always Run'
        on: push
        jobs:
          job1:
            if: false
            runs-on: ubuntu-latest
            steps:
              - run: echo "job1"
          job2:
            needs: job1
            if: always()
            runs-on: ubuntu-latest
            steps:
              - run: echo "job2"
        """
        workflow, problems = parse_workflow_string(workflow_string)
        analyzer = JobOrderer(Problems())
        execution_plan = analyzer._analyze_workflow(workflow)
        
        # job2 should still execute despite job1 being skipped
        assert len(execution_plan.stages) == 1
        assert len(execution_plan.stages[0].parallel_jobs) == 1
        assert execution_plan.stages[0].parallel_jobs[0].job_id_ == "job2"
        
        # job2 should be marked as always run
        assert "job2" in execution_plan.conditional_jobs
        assert execution_plan.conditional_jobs["job2"].always_run == True

    def test_context_based_conditions(self):
        """Jobs with context-based conditions should be analyzed correctly."""
        workflow_string = """
        name: 'Test Context Conditions'
        on: push
        jobs:
          job1:
            if: github.event_name == 'push'
            runs-on: ubuntu-latest
            steps:
              - run: echo "on push"
          job2:
            if: contains(github.event.head_commit.message, '[deploy]')
            runs-on: ubuntu-latest
            steps:
              - run: echo "deploy"
        """
        workflow, problems = parse_workflow_string(workflow_string)
        analyzer = JobOrderer(Problems())
        execution_plan = analyzer._analyze_workflow(workflow)
        
        # Both jobs should be tracked as conditional
        assert "job1" in execution_plan.conditional_jobs
        assert "job2" in execution_plan.conditional_jobs
        assert execution_plan.conditional_jobs["job1"].expression == "github.event_name == 'push'"
        assert execution_plan.conditional_jobs["job2"].expression == "contains(github.event.head_commit.message, '[deploy]')"


class TestJobOrderComplexPatterns:
    """Test complex job dependency patterns."""

    def test_fan_out_pattern(self):
        """Build job followed by multiple parallel test jobs."""
        workflow_string = """
        name: 'Test Fan-Out Pattern'
        on: push
        jobs:
          build:
            runs-on: ubuntu-latest
            steps:
              - run: echo "building"
          test-unit:
            needs: build
            runs-on: ubuntu-latest
            steps:
              - run: echo "unit tests"
          test-integration:
            needs: build
            runs-on: ubuntu-latest
            steps:
              - run: echo "integration tests"
          test-e2e:
            needs: build
            runs-on: ubuntu-latest
            steps:
              - run: echo "e2e tests"
        """
        workflow, problems = parse_workflow_string(workflow_string)
        analyzer = JobOrderer(Problems())
        execution_plan = analyzer._analyze_workflow(workflow)
        
        # Should have 2 stages: build first, then all tests in parallel
        assert len(execution_plan.stages) == 2
        assert len(execution_plan.stages[0].parallel_jobs) == 1
        assert execution_plan.stages[0].parallel_jobs[0].job_id_ == "build"
        assert len(execution_plan.stages[1].parallel_jobs) == 3
        test_jobs = {job.job_id_ for job in execution_plan.stages[1].parallel_jobs}
        assert test_jobs == {"test-unit", "test-integration", "test-e2e"}

    def test_fan_in_pattern(self):
        """Multiple parallel jobs followed by deploy job."""
        workflow_string = """
        name: 'Test Fan-In Pattern'
        on: push
        jobs:
          test-unit:
            runs-on: ubuntu-latest
            steps:
              - run: echo "unit tests"
          test-integration:
            runs-on: ubuntu-latest
            steps:
              - run: echo "integration tests"
          deploy:
            needs: [test-unit, test-integration]
            runs-on: ubuntu-latest
            steps:
              - run: echo "deploying"
        """
        workflow, problems = parse_workflow_string(workflow_string)
        analyzer = JobOrderer(Problems())
        execution_plan = analyzer._analyze_workflow(workflow)
        
        # Should have 2 stages: tests in parallel, then deploy
        assert len(execution_plan.stages) == 2
        assert len(execution_plan.stages[0].parallel_jobs) == 2
        test_jobs = {job.job_id_ for job in execution_plan.stages[0].parallel_jobs}
        assert test_jobs == {"test-unit", "test-integration"}
        assert len(execution_plan.stages[1].parallel_jobs) == 1
        assert execution_plan.stages[1].parallel_jobs[0].job_id_ == "deploy"

    def test_diamond_pattern(self):
        """Build -> [test, lint] -> deploy pattern."""
        workflow_string = """
        name: 'Test Diamond Pattern'
        on: push
        jobs:
          build:
            runs-on: ubuntu-latest
            steps:
              - run: echo "building"
          test:
            needs: build
            runs-on: ubuntu-latest
            steps:
              - run: echo "testing"
          lint:
            needs: build
            runs-on: ubuntu-latest
            steps:
              - run: echo "linting"
          deploy:
            needs: [test, lint]
            runs-on: ubuntu-latest
            steps:
              - run: echo "deploying"
        """
        workflow, problems = parse_workflow_string(workflow_string)
        analyzer = JobOrderer(Problems())
        execution_plan = analyzer._analyze_workflow(workflow)
        
        # Should have 3 stages: build -> [test, lint] -> deploy
        assert len(execution_plan.stages) == 3
        assert execution_plan.stages[0].parallel_jobs[0].job_id_ == "build"
        
        stage2_jobs = {job.job_id_ for job in execution_plan.stages[1].parallel_jobs}
        assert stage2_jobs == {"test", "lint"}
        
        assert execution_plan.stages[2].parallel_jobs[0].job_id_ == "deploy"

    def test_complex_mixed_dependencies(self):
        """Complex workflow with mixed dependency types."""
        workflow_string = """
        name: 'Test Complex Mixed Dependencies'
        on: push
        jobs:
          build:
            runs-on: ubuntu-latest
            steps:
              - run: echo "building"
          test:
            needs: build
            runs-on: ubuntu-latest
            steps:
              - run: echo "testing"
          lint:
            needs: build
            runs-on: ubuntu-latest
            steps:
              - run: echo "linting"
          security:
            runs-on: ubuntu-latest
            steps:
              - run: echo "security scan"
          deploy:
            needs: [test, lint, security]
            runs-on: ubuntu-latest
            steps:
              - run: echo "deploying"
          notify:
            needs: [build, security]
            if: always()
            runs-on: ubuntu-latest
            steps:
              - run: echo "notifying"
        """
        workflow, problems = parse_workflow_string(workflow_string)
        analyzer = JobOrderer(Problems())
        execution_plan = analyzer._analyze_workflow(workflow)
        
        # Should properly organize complex dependencies  
        assert len(execution_plan.stages) == 3
        
        # Stage 1: build and security (parallel)
        stage1_jobs = {job.job_id_ for job in execution_plan.stages[0].parallel_jobs}
        assert stage1_jobs == {"build", "security"}
        
        # Stage 2: test, lint, notify (all depend on stage 1 jobs)
        stage2_jobs = {job.job_id_ for job in execution_plan.stages[1].parallel_jobs}
        assert stage2_jobs == {"test", "lint", "notify"}
        
        # Stage 3: deploy (depends on test, lint, security)
        assert execution_plan.stages[2].parallel_jobs[0].job_id_ == "deploy"


class TestJobOrderMatrixStrategy:
    """Test job ordering with matrix strategies."""

    def test_matrix_job_dependencies(self):
        """Deploy should wait for ALL matrix instances to complete."""
        workflow_string = """
        name: 'Test Matrix Dependencies'
        on: push
        jobs:
          test:
            strategy:
              matrix:
                os: [ubuntu-latest, windows-latest, macos-latest]
            runs-on: ${{ matrix.os }}
            steps:
              - run: echo "testing on ${{ matrix.os }}"
          deploy:
            needs: test
            runs-on: ubuntu-latest
            steps:
              - run: echo "deploying"
        """
        workflow, problems = parse_workflow_string(workflow_string)
        analyzer = JobOrderer(Problems())
        execution_plan = analyzer._analyze_workflow(workflow)
        
        # Should have 2 stages: test matrix, then deploy
        assert len(execution_plan.stages) == 2
        # Matrix job should be treated as single logical job
        assert len(execution_plan.stages[0].parallel_jobs) == 1
        assert execution_plan.stages[0].parallel_jobs[0].job_id_ == "test"
        assert execution_plan.stages[1].parallel_jobs[0].job_id_ == "deploy"

    def test_matrix_with_fail_fast_false(self):
        """Matrix with fail-fast: false should still be properly ordered."""
        workflow_string = """
        name: 'Test Matrix Fail-Fast False'
        on: push
        jobs:
          test:
            strategy:
              matrix:
                os: [ubuntu-latest, windows-latest]
              fail-fast: false
            runs-on: ${{ matrix.os }}
            steps:
              - run: echo "testing"
          deploy:
            needs: test
            if: always()
            runs-on: ubuntu-latest
            steps:
              - run: echo "deploying"
        """
        workflow, problems = parse_workflow_string(workflow_string)
        analyzer = JobOrderer(Problems())
        execution_plan = analyzer._analyze_workflow(workflow)
        
        # Should still have proper ordering
        assert len(execution_plan.stages) == 2
        assert execution_plan.stages[0].parallel_jobs[0].job_id_ == "test"
        assert execution_plan.stages[1].parallel_jobs[0].job_id_ == "deploy"
        
        # Deploy should be marked as always run
        assert "deploy" in execution_plan.conditional_jobs
        assert execution_plan.conditional_jobs["deploy"].always_run == True


class TestJobOrderErrorConditions:
    """Test error conditions in job ordering."""

    def test_circular_dependency_detection(self):
        """Circular dependencies should be detected and reported."""
        workflow_string = """
        name: 'Test Circular Dependency'
        on: push
        jobs:
          job1:
            needs: job2
            runs-on: ubuntu-latest
            steps:
              - run: echo "job1"
          job2:
            needs: job1
            runs-on: ubuntu-latest
            steps:
              - run: echo "job2"
        """
        workflow, problems = parse_workflow_string(workflow_string)
        analyzer_problems = Problems()
        analyzer = JobOrderer(analyzer_problems)
        
        # Should detect circular dependency
        cycles = analyzer._detect_cycles(list(workflow.jobs_.values()), analyzer._build_dependency_graph(list(workflow.jobs_.values())))
        assert len(cycles) == 1
        assert isinstance(cycles[0], CyclicDependency)
        assert set(cycles[0].job_ids) == {"job1", "job2"}
        
        # Analyze workflow should collect problems in the Problems instance
        execution_plan = analyzer._analyze_workflow(workflow)
        assert len(analyzer_problems.problems) > 0
        circular_problems = [p for p in analyzer_problems.problems if "circular" in p.desc.lower()]
        assert len(circular_problems) > 0
        assert all(p.level == ProblemLevel.ERR for p in circular_problems)
        assert all(p.rule == "job-order-circular-dependency" for p in circular_problems)

    def test_self_dependency_detection(self):
        """Self-dependencies should be detected and reported."""
        workflow_string = """
        name: 'Test Self Dependency'
        on: push
        jobs:
          job1:
            needs: job1
            runs-on: ubuntu-latest
            steps:
              - run: echo "job1"
        """
        workflow, problems = parse_workflow_string(workflow_string)
        analyzer_problems = Problems()
        analyzer = JobOrderer(analyzer_problems)
        
        # Analyze workflow should collect problems in the Problems instance
        execution_plan = analyzer._analyze_workflow(workflow)
        assert len(analyzer_problems.problems) > 0
        self_dep_problems = [p for p in analyzer_problems.problems if "itself" in p.desc.lower()]
        assert len(self_dep_problems) > 0
        assert all(p.level == ProblemLevel.ERR for p in self_dep_problems)
        assert all(p.rule == "job-order-self-dependency" for p in self_dep_problems)

    def test_nonexistent_job_reference(self):
        """References to non-existent jobs should be detected."""
        workflow_string = """
        name: 'Test Non-existent Job Reference'
        on: push
        jobs:
          job1:
            needs: nonexistent_job
            runs-on: ubuntu-latest
            steps:
              - run: echo "job1"
        """
        workflow, problems = parse_workflow_string(workflow_string)
        analyzer_problems = Problems()
        analyzer = JobOrderer(analyzer_problems)
        
        # Analyze workflow should collect problems in the Problems instance  
        execution_plan = analyzer._analyze_workflow(workflow)
        assert len(analyzer_problems.problems) > 0
        invalid_ref_problems = [p for p in analyzer_problems.problems if "nonexistent_job" in p.desc]
        assert len(invalid_ref_problems) > 0
        assert all(p.level == ProblemLevel.ERR for p in invalid_ref_problems)
        assert all(p.rule == "job-order-invalid-reference" for p in invalid_ref_problems)

    def test_complex_circular_dependency(self):
        """Complex circular dependencies should be detected."""
        workflow_string = """
        name: 'Test Complex Circular Dependency'
        on: push
        jobs:
          job1:
            needs: job3
            runs-on: ubuntu-latest
            steps:
              - run: echo "job1"
          job2:
            needs: job1
            runs-on: ubuntu-latest
            steps:
              - run: echo "job2"
          job3:
            needs: job2
            runs-on: ubuntu-latest
            steps:
              - run: echo "job3"
        """
        workflow, problems = parse_workflow_string(workflow_string)
        analyzer_problems = Problems() 
        analyzer = JobOrderer(analyzer_problems)
        
        # Should detect circular dependency
        cycles = analyzer._detect_cycles(list(workflow.jobs_.values()), analyzer._build_dependency_graph(list(workflow.jobs_.values())))
        assert len(cycles) == 1
        assert set(cycles[0].job_ids) == {"job1", "job2", "job3"}
        
        # Analyze workflow should collect problems in the Problems instance
        execution_plan = analyzer._analyze_workflow(workflow)
        assert len(analyzer_problems.problems) > 0
        circular_problems = [p for p in analyzer_problems.problems if "circular" in p.desc.lower()]
        assert len(circular_problems) > 0
        assert all(p.level == ProblemLevel.ERR for p in circular_problems)
        assert all(p.rule == "job-order-circular-dependency" for p in circular_problems)


class TestJobOrderNeedsContextPopulation:
    """Test needs context population functionality."""

    def test_populate_workflow_needs_contexts_basic(self):
        """Test basic needs context population."""
        workflow_string = """
        name: 'Test Needs Context Population'
        on: push
        jobs:
          build:
            runs-on: ubuntu-latest
            outputs:
              version: "1.0.0"
            steps:
              - run: echo "building"
          test:
            needs: build
            runs-on: ubuntu-latest
            steps:
              - run: echo "testing"
        """
        workflow, problems = parse_workflow_string(workflow_string)
        
        # The needs context is already populated by parse_workflow_string
        test_job = workflow.jobs_["test"]
        
        # After population, test job should have build in needs context
        assert test_job.contexts.needs is not None
        assert "build" in test_job.contexts.needs.children_
        build_context = test_job.contexts.needs.children_["build"]
        from validate_actions.domain_model.contexts import ContextType
        assert build_context.type_ == ContextType.object
        assert build_context.result == ContextType.string
        
        # Steps should also have the same needs context
        for step in test_job.steps_:
            assert step.contexts.needs is not None
            assert "build" in step.contexts.needs.children_

    def test_populate_workflow_needs_contexts_no_dependencies(self):
        """Test needs context population with no dependencies."""
        workflow_string = """
        name: 'Test No Dependencies'
        on: push
        jobs:
          job1:
            runs-on: ubuntu-latest
            steps:
              - run: echo "job1"
          job2:
            runs-on: ubuntu-latest
            steps:
              - run: echo "job2"
        """
        workflow, problems = parse_workflow_string(workflow_string)
        analyzer = JobOrderer(Problems())
        
        # Populate needs contexts
        analyzer.prepare_workflow(workflow)
        
        # Jobs with no dependencies should have empty needs contexts
        for job in workflow.jobs_.values():
            assert job.contexts.needs is not None
            assert len(job.contexts.needs.children_) == 0
            for step in job.steps_:
                assert step.contexts.needs is not None
                assert len(step.contexts.needs.children_) == 0


class TestJobOrderIntegrationWithExistingRules:
    """Test integration of job ordering with existing validation rules."""

    def test_expression_contexts_with_job_order(self):
        """ExpressionsContexts rule should understand job execution order."""
        workflow_string = """
        name: 'Test Expression Context with Job Order'
        on: push
        jobs:
          build:
            runs-on: ubuntu-latest
            outputs:
              artifact-name: ${{ steps.checkout.outputs.ref }}
            steps:
              - id: checkout
                uses: actions/checkout@v4
          test:
            needs: build
            runs-on: ubuntu-latest
            steps:
              - name: Use build output
                run: echo "Testing ${{ needs.build.outputs.artifact-name }}"
          invalid_test:
            runs-on: ubuntu-latest
            steps:
              - name: Invalid reference
                run: echo "Testing ${{ needs.build.outputs.artifact-name }}"  # build not a dependency
        """
        workflow, problems = parse_workflow_string(workflow_string)
        analyzer = JobOrderer(Problems())
        execution_plan = analyzer._analyze_workflow(workflow)
        
        # Job order should be: build -> test (parallel with invalid_test)
        assert len(execution_plan.stages) == 2
        
        # Populate needs contexts using the new interface
        analyzer.prepare_workflow(workflow)
        
        # When integrated with ExpressionsContexts rule:
        # - test job should be valid (build is a dependency)
        # - invalid_test job should be invalid (build is not a dependency)
        from validate_actions import analyze
        rule = analyze.ExpressionsContexts(workflow, False, None)
        problems = list(rule.check())

        assert len(problems) == 1
        assert problems[0].level == ProblemLevel.ERR
        assert "needs.build.outputs.artifact-name" in problems[0].desc
        assert problems[0].pos.line == 21  # Line of invalid_test job

        assert execution_plan.stages[0].parallel_jobs[0].job_id_ == "build"
        stage2_jobs = {job.job_id_ for job in execution_plan.stages[1].parallel_jobs}
        assert stage2_jobs == {"test"}


class TestJobOrderPerformance:
    """Test job ordering performance with large workflows."""

    def test_large_workflow_performance(self):
        """Job ordering should handle large workflows efficiently."""
        # Generate a large workflow with many jobs
        jobs_yaml = []
        for i in range(100):
            if i == 0:
                jobs_yaml.append(f"""
          job_{i}:
            runs-on: ubuntu-latest
            steps:
              - run: echo "job {i}"
                """)
            else:
                jobs_yaml.append(f"""
          job_{i}:
            needs: job_{i-1}
            runs-on: ubuntu-latest
            steps:
              - run: echo "job {i}"
                """)
        
        workflow_string = f"""
        name: 'Test Large Workflow'
        on: push
        jobs:{''.join(jobs_yaml)}
        """
        
        workflow, problems = parse_workflow_string(workflow_string)
        analyzer = JobOrderer(Problems())
        
        # This should complete reasonably quickly
        import time
        start_time = time.time()
        execution_plan = analyzer._analyze_workflow(workflow)
        end_time = time.time()
        
        # Should complete in reasonable time (< 1 second)
        assert end_time - start_time < 1.0
        
        # Should have 100 stages (linear execution)
        assert len(execution_plan.stages) == 100
        
        # Each stage should have exactly one job
        for i, stage in enumerate(execution_plan.stages):
            assert len(stage.parallel_jobs) == 1
            assert stage.parallel_jobs[0].job_id_ == f"job_{i}"

    def test_wide_workflow_performance(self):
        """Job ordering should handle workflows with many parallel jobs."""
        # Generate a workflow with many parallel jobs
        jobs_yaml = []
        for i in range(50):
            jobs_yaml.append(f"""
          job_{i}:
            runs-on: ubuntu-latest
            steps:
              - run: echo "job {i}"
            """)
        
        # Add a final job that depends on all others
        dependency_list = ", ".join([f"job_{i}" for i in range(50)])
        jobs_yaml.append(f"""
          final_job:
            needs: [{dependency_list}]
            runs-on: ubuntu-latest
            steps:
              - run: echo "final job"
        """)
        
        workflow_string = f"""
        name: 'Test Wide Workflow'
        on: push
        jobs:{''.join(jobs_yaml)}
        """
        
        workflow, problems = parse_workflow_string(workflow_string)
        analyzer = JobOrderer(Problems())
        
        # This should complete reasonably quickly
        import time
        start_time = time.time()
        execution_plan = analyzer._analyze_workflow(workflow)
        end_time = time.time()
        
        # Should complete in reasonable time (< 1 second)
        assert end_time - start_time < 1.0
        
        # Should have 2 stages: 50 parallel jobs, then 1 final job
        assert len(execution_plan.stages) == 2
        assert len(execution_plan.stages[0].parallel_jobs) == 50
        assert len(execution_plan.stages[1].parallel_jobs) == 1
        assert execution_plan.stages[1].parallel_jobs[0].job_id_ == "final_job"