# flake8: noqa: E501

import tempfile
from pathlib import Path

from tests.helper import parse_workflow_string
from validate_actions import analyzing
from validate_actions.core.problems import Problem, ProblemLevel
from validate_actions.fixing.fixer import BaseFixer


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
    rule = analyzing.ExpressionsContexts(workflow_matches, False, None)
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
    workflow_doesnt_match, problems_doesnt_match = parse_workflow_string(
        workflow_doesnt_match_string
    )
    rule = analyzing.ExpressionsContexts(workflow_doesnt_match, False, None)
    gen_doesnt_match = rule.check()
    result_doesnt_match = list(gen_doesnt_match)
    assert len(result_doesnt_match) == 1
    assert result_doesnt_match[0].rule == "expressions-contexts"


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
    rule = analyzing.ExpressionsContexts(workflow, False, None)
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
    rule = analyzing.ExpressionsContexts(workflow, False, None)
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
    rule = analyzing.ExpressionsContexts(workflow, False, None)
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
    rule = analyzing.ExpressionsContexts(workflow, False, None)
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
    rule = analyzing.ExpressionsContexts(workflow, False, None)
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
        with tempfile.NamedTemporaryFile(
            mode="w+", delete=False, suffix=".yml", encoding="utf-8"
        ) as f:
            f.write(workflow_string_with_typo)
            temp_file_path = Path(f.name)

        # Parse the workflow string (content is what matters for parsing positions)
        workflow_obj, initial_problems = parse_workflow_string(workflow_string_with_typo)

        # Assuming the parser itself doesn't find problems with this specific typo,
        # or that such problems are not relevant to this test's focus.
        # If initial_problems could contain the typo, you might want to assert its presence here.

        # Run the check with fix=True
        # The check function modifies the file in place if a fix is applied
        fixer = BaseFixer(temp_file_path)
        rule = analyzing.ExpressionsContexts(workflow_obj, True, fixer)
        problems_after_fix = list(rule.check())
        # Apply the batched fixes
        fixer.flush()

        # Assert that the problem was fixed and non problem is reported for this specific issue
        assert len(problems_after_fix) == 1
        assert problems_after_fix[0].level == ProblemLevel.NON  # No problems should remain

        # Read the content of the modified file
        fixed_content = temp_file_path.read_text(encoding="utf-8")

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
        with tempfile.NamedTemporaryFile(
            mode="w+", delete=False, suffix=".yml", encoding="utf-8"
        ) as f:
            f.write(workflow_string_with_typo)
            temp_file_path = Path(f.name)

        workflow_obj, initial_problems = parse_workflow_string(workflow_string_with_typo)
        fixer = BaseFixer(temp_file_path)
        rule = analyzing.ExpressionsContexts(workflow_obj, True, fixer)
        problems_after_fix = list(rule.check())
        # Apply the batched fixes
        fixer.flush()
        # Assert that the problem was fixed and non problem is reported for this specific issue
        assert len(problems_after_fix) == 1
        assert problems_after_fix[0].level == ProblemLevel.NON  # No problems should remain
        fixed_content = temp_file_path.read_text(encoding="utf-8")
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
        with tempfile.NamedTemporaryFile(
            mode="w+", delete=False, suffix=".yml", encoding="utf-8"
        ) as f:
            f.write(workflow_string_with_typo)
            temp_file_path = Path(f.name)

        workflow_obj, initial_problems = parse_workflow_string(workflow_string_with_typo)
        fixer = BaseFixer(temp_file_path)
        rule = analyzing.ExpressionsContexts(workflow_obj, True, fixer)
        problems_after_fix = list(rule.check())
        # Apply the batched fixes
        fixer.flush()
        assert not problems_after_fix
        fixed_content = temp_file_path.read_text(encoding="utf-8")
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
        with tempfile.NamedTemporaryFile(
            mode="w+", delete=False, suffix=".yml", encoding="utf-8"
        ) as f:
            f.write(workflow_string_with_typo)
            temp_file_path = Path(f.name)

        workflow_obj, initial_problems = parse_workflow_string(workflow_string_with_typo)
        fixer = BaseFixer(temp_file_path)
        rule = analyzing.ExpressionsContexts(workflow_obj, True, fixer)
        problems_after_fix = list(rule.check())
        # Apply the batched fixes
        fixer.flush()
        # Assert that the problem was fixed and non problem is reported for this specific issue
        assert len(problems_after_fix) == 1
        assert problems_after_fix[0].level == ProblemLevel.NON  # No problems should remain
        fixed_content = temp_file_path.read_text(encoding="utf-8")
        assert fixed_content.strip() == expected_fixed.strip()
    finally:
        if temp_file_path:
            temp_file_path.unlink(missing_ok=True)


def test_fix_two_expression_context_typos():
    workflow_string_with_typos = """
    name: Build
    on: push

    jobs:
      build:
        runs-on: ubuntu-latest
        services:
          redis:
            image: redis
            ports:
              - 6379/tcp
        steps:
          - uses: actions/checkout@v4
          - name: Build with logs
            run: |
              mkdir ${{ runer.temp }}/build_logs
              echo "Logs from building" > ${{ runner.temp }}/build_logs/build.logs
          - name: Use service port
            run: echo "${{ job.servics.redis.ports['6379'] }}"
    """
    expected_workflow_string_fixed = """
    name: Build
    on: push

    jobs:
      build:
        runs-on: ubuntu-latest
        services:
          redis:
            image: redis
            ports:
              - 6379/tcp
        steps:
          - uses: actions/checkout@v4
          - name: Build with logs
            run: |
              mkdir ${{ runner.temp }}/build_logs
              echo "Logs from building" > ${{ runner.temp }}/build_logs/build.logs
          - name: Use service port
            run: echo "${{ job.services.redis.ports['6379'] }}"
    """

    temp_file_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w+", delete=False, suffix=".yml", encoding="utf-8"
        ) as f:
            f.write(workflow_string_with_typos)
            temp_file_path = Path(f.name)

        workflow_obj, initial_problems = parse_workflow_string(workflow_string_with_typos)

        fixer = BaseFixer(temp_file_path)
        rule = analyzing.ExpressionsContexts(workflow_obj, True, fixer)
        problems_after_fix = list(rule.check())
        # Apply the batched fixes
        fixer.flush()

        # Assert that the problems were fixed and no problem is reported for these specific issues
        assert len(problems_after_fix) == 2
        assert all(p.level == ProblemLevel.NON for p in problems_after_fix)

        fixed_content = temp_file_path.read_text(encoding="utf-8")
        assert fixed_content.strip() == expected_workflow_string_fixed.strip()

    finally:
        if temp_file_path:
            temp_file_path.unlink(missing_ok=True)
