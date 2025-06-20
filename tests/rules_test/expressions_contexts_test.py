# flake8: noqa: E501

import tempfile
from pathlib import Path

from tests.helper import parse_workflow_string
from validate_actions import rules
from validate_actions.fixer import BaseFixer
from validate_actions.problems import Problem, ProblemLevel


def test_job_outputs_input_match():
    workflow_matches_string = """
    name: Reusable workflow

    on:
      workflow_call:

        # Map the workflow outputs to job outputs
        outputs:
          firstword:
            description: "The first output string"
            value: ${{ jobs.example_job.outputs.output1 }}
          secondword:
            description: "The second output string"
            value: ${{ jobs.example_job.outputs.output2 }}

    jobs:
      example_job:
        name: Generate output
        runs-on: ubuntu-latest
        
        # Map the job outputs to step outputs
        outputs:
          output1: ${{ steps.step1.outputs.firstword }}
          output2: ${{ steps.step2.outputs.secondword }}
        
        steps:
        - id: step1
          run: echo "firstword=hello" >> $GITHUB_OUTPUT
        - id: step2
          run: echo "secondword=world" >> $GITHUB_OUTPUT
    """
    workflow_matches, problems_matches = parse_workflow_string(workflow_matches_string)
    rule = rules.ExpressionsContexts(workflow_matches, False, None)
    gen_matches = rule.check()
    result_matches = list(gen_matches)
    assert result_matches == []
    
    workflow_doesnt_match_string = """
    name: Reusable workflow

    on:
      workflow_call:

        # Map the workflow outputs to job outputs
        outputs:
          firstword:
            description: "The first output string"
            value: ${{ jobs.example_job.outputs.out1 }}
          secondword:
            description: "The second output string"
            value: ${{ jobs.example_job.outputs.output2 }}

    jobs:
      example_job:
        name: Generate output
        runs-on: ubuntu-latest
        
        # Map the job outputs to step outputs
        outputs:
          output1: ${{ steps.step1.outputs.firstword }}
          output2: ${{ steps.step2.outputs.secondword }}
        
        steps:
        - id: step1
          run: echo "firstword=hello" >> $GITHUB_OUTPUT
        - id: step2
          run: echo "secondword=world" >> $GITHUB_OUTPUT
    """
    workflow_doesnt_match, problems_doesnt_match = parse_workflow_string(workflow_doesnt_match_string)
    rule = rules.ExpressionsContexts(workflow_doesnt_match, False, None)
    gen_doesnt_match = rule.check()
    result_doesnt_match = list(gen_doesnt_match)
    assert len(result_doesnt_match) == 1
    assert result_doesnt_match[0].rule == 'expressions-contexts'

def test_env_match():
    workflow_string = """
    name: 'Test Steps IO Match with uses'

    on: workflow_dispatch
    
    env:
      my_var: 'some_value'

    jobs:
      test-job:
        runs-on: ubuntu-latest
        steps:

        - id: step2
          name: 'Upload artifact'
          uses: actions/upload-artifact@v3
          with:
            name: my-artifact
            path: ${{ env.my_var }}  # Reference to output from env var
    """
    workflow, problems = parse_workflow_string(workflow_string)
    rule = rules.ExpressionsContexts(workflow, False, None)
    gen = rule.check()
    result = list(gen)
    assert result == []
    
    workflow_string = """
    name: 'Test Steps IO Match with uses'

    on: workflow_dispatch
    
    env:
      my_var: 'some_value'

    jobs:
      test-job:
        runs-on: ubuntu-latest
        steps:

        - id: step2
          name: 'Upload artifact'
          uses: actions/upload-artifact@v3
          with:
            name: my-artifact
            path: ${{ env.myvar }}  # Reference to output from non-existent env var
    """
    workflow, problems = parse_workflow_string(workflow_string)
    rule = rules.ExpressionsContexts(workflow, False, None)
    gen = rule.check()
    result = list(gen)
    assert len(result) == 1

def test_local_env():
    workflow_string = """
    name: 'Test Steps IO Match with uses'

    on: workflow_dispatch
    
    env:
      global_path: 'path/to/artifact'

    jobs:
      test-job:
        runs-on: ubuntu-latest
        env:
          job_path: 'path/to/job_artifact'  # job-level env var
        steps:
        - id: step1
          name: 'Upload artifact'
          uses: actions/upload-artifact@v3
          with:
            name: global-artifact
            path: ${{ env.global_path }}  # Reference to output from env var
        - id: step2
          name: 'Upload artifact'
          uses: actions/upload-artifact@v3
          with:
            name: job-artifact
            path: ${{ env.job_path }}  # job-level
        - id: step3
          name: 'Upload artifact'
          uses: actions/upload-artifact@v3
          env:
            step_path: 'path/to/step_artifact'  # step-level env var
          with:
            name: step-artifact
            path: ${{ env.step_path }}  # step-level
        - id: step4
          name: 'Upload artifact'
          uses: actions/upload-artifact@v3
          with:
            name: step-artifact
            path: ${{ env.step_path }}  # step-level wrong, not in this step
      test-job2:
        runs-on: ubuntu-latest
        steps:
        - id: step5
          name: 'Upload artifact'
          uses: actions/upload-artifact@v3
          with:
            name: job2-artifact
            name: ${{ env.job_path }}  # job-level wrong, not in this job
    """
    workflow, problems = parse_workflow_string(workflow_string)
    rule = rules.ExpressionsContexts(workflow, False, None)
    gen = rule.check()
    result = list(gen)
    assert len(result) == 2
    assert result[0].pos.line == 39
    assert result[1].pos.line == 48


def test_job_context_correct():
    workflow_string = """
    on: push
    jobs:
      job:
        runs-on: ubuntu-latest
        services:
          nginx:
            image: nginx
            # Map port 8080 on the Docker host to port 80 on the nginx container
            ports:
              - 8080:80
          redis:
            image: redis
            # Map random free TCP port on Docker host to port 6379 on redis container
            ports:
              - 6379/tcp
        steps:
        - name: Start MongoDB
          uses: supercharge/mongodb-github-action@1.12.0
          with:
            mongodb-port: ${{ job.services.redis.ports['6379'] }}
    """
    workflow, problems = parse_workflow_string(workflow_string)
    rule = rules.ExpressionsContexts(workflow, False, None)
    gen = rule.check()
    result = list(gen)
    assert result == []


def test_job_context_incorrect():
    workflow_string = """
    on: push
    jobs:
      job:
        runs-on: ubuntu-latest
        services:
          nginx:
            image: nginx
            # Map port 8080 on the Docker host to port 80 on the nginx container
            ports:
              - 8080:80
          redis:
            image: redis
            # Map random free TCP port on Docker host to port 6379 on redis container
            ports:
              - 6379/tcp
        steps:
        - name: Start MongoDB
          uses: supercharge/mongodb-github-action@1.12.0
          with:
            mongodb-port: ${{ job.services.redis.ports['379'] }}
    """
    workflow, problems = parse_workflow_string(workflow_string)
    rule = rules.ExpressionsContexts(workflow, False, None)
    gen = rule.check()
    result = list(gen)
    assert len(result) == 1


def test_runner_context_correct():
    workflow_string = """
    name: Build
    on: push

    jobs:
      build:
        runs-on: ubuntu-latest
        steps:
          - uses: actions/checkout@v4
          - name: Build with logs
            run: |
              mkdir ${{ runner.temp }}/build_logs
              echo "Logs from building" > ${{ runner.temp }}/build_logs/build.logs
              exit 1
          - name: Upload logs on fail
            if: ${{ failure() }}
            uses: actions/upload-artifact@v4
            with:
              name: Build failure logs
              path: ${{ runner.temp }}/build_logs
    """
    workflow, problems = parse_workflow_string(workflow_string)
    rule = rules.ExpressionsContexts(workflow, False, None)
    gen = rule.check()
    result = list(gen)
    assert len(result) == 0


def test_runner_context_wrong():
    workflow_string = """
    name: Build
    on: push

    jobs:
      build:
        runs-on: ubuntu-latest
        steps:
          - uses: actions/checkout@v4
          - name: Build with logs
            run: |
              mkdir ${{ runner.temmp }}/build_logs  # error
              echo "Logs from building" > ${{ runner.temp }}/build_logs/build.logs
              exit 1
          - name: Upload logs on fail
            if: ${{ failure() }}
            uses: actions/upload-artifact@v4
            with:
              name: Build failure logs
              path: ${{ runner.temp }}/build_logs
    """
    workflow, problems = parse_workflow_string(workflow_string)
    rule = rules.ExpressionsContexts(workflow, False, None)
    gen = rule.check()
    result = list(gen)
    assert len(result) == 1


def test_web_context():
    workflow_string = """
    on:workflow_dispatch
    env:
      # Setting an environment variable with the value of a configuration variable
      env_var: ${{ vars.ENV_CONTEXT_VAR }}

    jobs:
      display-variables:
        name: ${{ vars.JOB_NAME }}
        # You can use configuration variables with the `vars` context for dynamic jobs
        if: ${{ vars.USE_VARIABLES == 'true' }}
        runs-on: ${{ vars.RUNNER }}
        environment: ${{ vars.ENVIRONMENT_STAGE }}
        steps:
        - name: Use variables
          run: |
            echo "repository variable : $REPOSITORY_VAR"
            echo "organization variable : $ORGANIZATION_VAR"
            echo "overridden variable : $OVERRIDE_VAR"
            echo "variable from shell environment : $env_var"
          env:
            REPOSITORY_VAR: ${{ vars.REPOSITORY_VAR }}
            ORGANIZATION_VAR: ${{ vars.ORGANIZATION_VAR }}
            OVERRIDE_VAR: ${{ vars.OVERRIDE_VAR }}
            
        - name: ${{ vars.HELLO_WORLD_STEP }}
          if: ${{ vars.HELLO_WORLD_ENABLED == 'true' }}
          uses: actions/hello-world-javascript-action@main
          with:
        who-to-greet: ${{ vars.GREET_NAME }}
    """
    workflow, problems = parse_workflow_string(workflow_string)
    rule = rules.ExpressionsContexts(workflow, False, None)
    gen = rule.check()
    result = list(gen)
    assert result == []


def test_fix_expression_context_typo():
    workflow_string_with_typo = """
    name: Build
    on: push

    jobs:
      build:
        runs-on: ubuntu-latest
        steps:
          - uses: actions/checkout@v4
          - name: Build with logs
            run: |
              mkdir ${{ runer.temp }}/build_logs
              echo "Logs from building" > ${{ runner.temp }}/build_logs/build.logs
              exit 1
          - name: Upload logs on fail
            if: ${{ failure() }}
            uses: actions/upload-artifact@v4
            with:
              name: Build failure logs
              path: ${{ runner.temp }}/build_logs
    """
    expected_workflow_string_fixed = """
    name: Build
    on: push

    jobs:
      build:
        runs-on: ubuntu-latest
        steps:
          - uses: actions/checkout@v4
          - name: Build with logs
            run: |
              mkdir ${{ runner.temp }}/build_logs
              echo "Logs from building" > ${{ runner.temp }}/build_logs/build.logs
              exit 1
          - name: Upload logs on fail
            if: ${{ failure() }}
            uses: actions/upload-artifact@v4
            with:
              name: Build failure logs
              path: ${{ runner.temp }}/build_logs
    """

    temp_file_path = None
    try:
        # Create a named temporary file
        with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.yml', encoding='utf-8') as f:
            f.write(workflow_string_with_typo)
            temp_file_path = Path(f.name)

        # Parse the workflow string (content is what matters for parsing positions)
        workflow_obj, initial_problems = parse_workflow_string(workflow_string_with_typo)
        
        # Assuming the parser itself doesn't find problems with this specific typo,
        # or that such problems are not relevant to this test's focus.
        # If initial_problems could contain the typo, you might want to assert its presence here.

        # IMPORTANT: Set the path attribute on the workflow object to the temp file
        workflow_obj.path = temp_file_path

        # Run the check with fix=True
        # The check function modifies the file in place if a fix is applied
        fixer = BaseFixer(temp_file_path)
        rule = rules.ExpressionsContexts(workflow_obj, True, fixer)
        problems_after_fix = list(rule.check())

        # Assert that the problem was fixed and non problem is reported for this specific issue
        assert len(problems_after_fix) == 1
        assert problems_after_fix[0].level == ProblemLevel.NON  # No problems should remain

        # Read the content of the modified file
        fixed_content = temp_file_path.read_text(encoding='utf-8')

        # Assert that the file content is as expected
        # Using strip() to handle potential differences in trailing newlines
        assert fixed_content.strip() == expected_workflow_string_fixed.strip()

    finally:
        if temp_file_path:
            temp_file_path.unlink(missing_ok=True)

def test_fix_service_port_typo():
    workflow_string_with_typo = """
    on: push
    jobs:
      job:
        runs-on: ubuntu-latest
        services:
          redis:
            image: redis
            ports:
              - 6379/tcp
        steps:
        - name: Use service port
          run: echo "Port is ${{ job.services.redis.ports['379'] }}"
    """
    expected_fixed = """
    on: push
    jobs:
      job:
        runs-on: ubuntu-latest
        services:
          redis:
            image: redis
            ports:
              - 6379/tcp
        steps:
        - name: Use service port
          run: echo "Port is ${{ job.services.redis.ports['6379'] }}"
    """
    temp_file_path = None
    try:
        with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.yml', encoding='utf-8') as f:
            f.write(workflow_string_with_typo)
            temp_file_path = Path(f.name)

        workflow_obj, initial_problems = parse_workflow_string(workflow_string_with_typo)
        workflow_obj.path = temp_file_path
        fixer = BaseFixer(temp_file_path)
        rule = rules.ExpressionsContexts(workflow_obj, True, fixer)
        problems_after_fix = list(rule.check())
        # Assert that the problem was fixed and non problem is reported for this specific issue
        assert len(problems_after_fix) == 1
        assert problems_after_fix[0].level == ProblemLevel.NON  # No problems should remain
        fixed_content = temp_file_path.read_text(encoding='utf-8')
        assert fixed_content.strip() == expected_fixed.strip()
    finally:
        if temp_file_path:
            temp_file_path.unlink(missing_ok=True)

def test_fix_multiple_expressions_in_string():
    workflow_string_with_typo = """
    on: push
    jobs:
      job:
        runs-on: ubuntu-latest
        steps:
        - name: Combined expressions
          run: 'echo "First: ${{ runner.temp }}, Second: ${{ runner.temp }}/dir"'
    """
    expected_fixed = """
    on: push
    jobs:
      job:
        runs-on: ubuntu-latest
        steps:
        - name: Combined expressions
          run: 'echo "First: ${{ runner.temp }}, Second: ${{ runner.temp }}/dir"'
    """
    temp_file_path = None
    try:
        with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.yml', encoding='utf-8') as f:
            f.write(workflow_string_with_typo)
            temp_file_path = Path(f.name)

        workflow_obj, initial_problems = parse_workflow_string(workflow_string_with_typo)
        workflow_obj.path = temp_file_path
        fixer = BaseFixer(temp_file_path)
        rule = rules.ExpressionsContexts(workflow_obj, True, fixer)
        problems_after_fix = list(rule.check())
        assert not problems_after_fix
        fixed_content = temp_file_path.read_text(encoding='utf-8')
        assert fixed_content.strip() == expected_fixed.strip()
    finally:
        if temp_file_path:
            temp_file_path.unlink(missing_ok=True)

def test_fix_typo_in_middle_of_expression():
    workflow_string_with_typo = """
    on: push
    jobs:
      job:
        runs-on: ubuntu-latest
        steps:
        - name: Service with typo
          run: echo "${{ job.servics.redis.ports['6379'] }}"
    """
    expected_fixed = """
    on: push
    jobs:
      job:
        runs-on: ubuntu-latest
        steps:
        - name: Service with typo
          run: echo "${{ job.services.redis.ports['6379'] }}"
    """
    temp_file_path = None
    try:
        with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.yml', encoding='utf-8') as f:
            f.write(workflow_string_with_typo)
            temp_file_path = Path(f.name)

        workflow_obj, initial_problems = parse_workflow_string(workflow_string_with_typo)
        workflow_obj.path = temp_file_path
        fixer = BaseFixer(temp_file_path)
        rule = rules.ExpressionsContexts(workflow_obj, True, fixer)
        problems_after_fix = list(rule.check())
        # Assert that the problem was fixed and non problem is reported for this specific issue
        assert len(problems_after_fix) == 1
        assert problems_after_fix[0].level == ProblemLevel.NON  # No problems should remain
        fixed_content = temp_file_path.read_text(encoding='utf-8')
        assert fixed_content.strip() == expected_fixed.strip()
    finally:
        if temp_file_path:
            temp_file_path.unlink(missing_ok=True)