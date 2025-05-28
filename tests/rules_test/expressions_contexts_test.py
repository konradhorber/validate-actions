# flake8: noqa: E501

from tests.helper import parse_workflow_string
from validate_actions import rules
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
    gen_matches = rules.ExpressionsContexts.check(workflow_matches)
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
    gen_doesnt_match = rules.ExpressionsContexts.check(workflow_doesnt_match)
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
    gen = rules.StepsIOMatch.check(workflow)
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
    gen = rules.ExpressionsContexts.check(workflow)
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
    gen = rules.ExpressionsContexts.check(workflow)
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
    gen = rules.ExpressionsContexts.check(workflow)
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
    gen = rules.ExpressionsContexts.check(workflow)
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
    gen = rules.ExpressionsContexts.check(workflow)
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
    gen = rules.ExpressionsContexts.check(workflow)
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
    gen = rules.ExpressionsContexts.check(workflow)
    result = list(gen)
    assert result == []