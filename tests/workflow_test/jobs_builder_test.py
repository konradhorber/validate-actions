# flake8: noqa: E501

from tests.helper import parse_workflow_string
from validate_actions.workflow import ast, contexts


def test_job_env():
    workflow_string = """
on: push
jobs:
  build:
    runs-on: ubuntu-latest
    env:
      GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
      FIRST_NAME: Mona
      LAST_NAME: Octocat
    steps:
      - name: Checkout
        uses: actions/checkout@v4
"""
    workflow_out, problems = parse_workflow_string(workflow_string)
    env_ = workflow_out.jobs_['build'].env_
    assert problems.problems == []
    assert env_.get('GITHUB_TOKEN').string == '${{ secrets.GITHUB_TOKEN }}'
    assert env_.get('FIRST_NAME').string == 'Mona'
    assert env_.get('LAST_NAME').string == 'Octocat'


def test_step_env():
    workflow_string = """
on: push
jobs:
  build:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v4
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          FIRST_NAME: Mona
          LAST_NAME: Octocat
"""
    workflow_out, problems = parse_workflow_string(workflow_string)
    env_ = workflow_out.jobs_['build'].steps_[0].env_
    assert problems.problems == []
    assert env_.get('GITHUB_TOKEN').string == '${{ secrets.GITHUB_TOKEN }}'
    assert env_.get('FIRST_NAME').string == 'Mona'
    assert env_.get('LAST_NAME').string == 'Octocat'


def test_step_timeout_minutes():
    workflow_string = """
on: push
jobs:
  build:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v4
        timeout-minutes: 10
"""
    workflow_out, problems = parse_workflow_string(workflow_string)
    timeout_minutes_ = workflow_out.jobs_['build'].steps_[0].timeout_minutes_
    assert problems.problems == []
    assert timeout_minutes_ == 10


def test_step_continue_on_error():
    workflow_string = """
on: push
jobs:
  build:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v4
        continue-on-error: true
"""
    workflow_out, problems = parse_workflow_string(workflow_string)
    continue_on_error_ = workflow_out.jobs_['build'].steps_[0].continue_on_error_
    assert problems.problems == []
    assert continue_on_error_ is True


# Integration tests for job-level defaults using parse_workflow_string

def test_job_defaults_shell():
    workflow_string = """
on: push
jobs:
  build:
    defaults:
      run:
        shell: pwsh
    runs-on: ubuntu-latest
    steps:
      - name: Echo
        run: echo hi
"""
    workflow_out, problems = parse_workflow_string(workflow_string)
    defaults = workflow_out.jobs_['build'].defaults_
    assert len(problems.problems) == 0
    assert defaults is not None
    assert defaults.shell_.value == "pwsh"
    assert defaults.working_directory_ is None


def test_job_defaults_working_directory():
    workflow_string = """
on: push
jobs:
  build:
    defaults:
      run:
        working-directory: /home/user
    runs-on: ubuntu-latest
    steps:
      - name: Echo
        run: echo hi
"""
    workflow_out, problems = parse_workflow_string(workflow_string)
    defaults = workflow_out.jobs_['build'].defaults_
    assert len(problems.problems) == 0
    assert defaults is not None
    assert defaults.shell_ is None
    assert defaults.working_directory_.string == "/home/user"


def test_job_defaults_shell_and_working_directory():
    workflow_string = """
on: push
jobs:
  build:
    defaults:
      run:
        shell: sh
        working-directory: /tmp
    runs-on: ubuntu-latest
    steps:
      - name: Echo
        run: echo hi
"""
    workflow_out, problems = parse_workflow_string(workflow_string)
    defaults = workflow_out.jobs_['build'].defaults_
    assert len(problems.problems) == 0
    assert defaults is not None
    assert defaults.shell_.value == "sh"
    assert defaults.working_directory_.string == "/tmp"


def test_job_defaults_invalid_structure():
    workflow_string = """
on: push
jobs:
  build:
    defaults: not_a_map
    runs-on: ubuntu-latest
    steps:
      - name: Echo
        run: echo hi
"""
    workflow_out, problems = parse_workflow_string(workflow_string)
    assert workflow_out.jobs_['build'].defaults_ is None
    assert any(p.desc.startswith("Invalid 'defaults:'") for p in problems.problems)


def test_job_defaults_invalid_shell():
    workflow_string = """
on: push
jobs:
  build:
    defaults:
      run:
        shell: fish
    runs-on: ubuntu-latest
    steps:
      - name: Echo
        run: echo hi
"""
    workflow_out, problems = parse_workflow_string(workflow_string)
    assert workflow_out.jobs_['build'].defaults_ is None
    assert any(p.desc == "Invalid shell: fish" for p in problems.problems)


def test_job_permissions_single():
    workflow_string = """
on: push
jobs:
  stale:
    runs-on: ubuntu-latest

    permissions:
      issues: write
      pull-requests: read
      pull_request_review: none

    steps:
      - uses: actions/stale@v9
"""
    workflow_out, problems = parse_workflow_string(workflow_string)
    permissions_ = workflow_out.jobs_['stale'].permissions_
    assert problems.problems[0].desc == "Invalid permission: pull_request_review"
    assert permissions_.issues_ == ast.Permission.write
    assert permissions_.pull_requests_ == ast.Permission.read
    assert permissions_.id_token_ == ast.Permission.none
    assert permissions_.contents_ == ast.Permission.write


def test_job_permissions_bulk():
    workflow_string = """
on: push
jobs:
  stale:
    runs-on: ubuntu-latest

    permissions: read-all

    steps:
      - uses: actions/stale@v9
"""
    workflow_out, problems = parse_workflow_string(workflow_string)
    permissions_ = workflow_out.jobs_['stale'].permissions_
    assert problems.problems == []
    assert permissions_.issues_ == ast.Permission.read
    assert permissions_.pull_requests_ == ast.Permission.read


def test_job_permissions_none():
    workflow_string = """
on: push
jobs:
  stale:
    runs-on: ubuntu-latest

    permissions: {}

    steps:
      - uses: actions/stale@v9
"""
    workflow_out, problems = parse_workflow_string(workflow_string)
    permissions_ = workflow_out.jobs_['stale'].permissions_
    assert problems.problems == []
    assert permissions_.issues_ == ast.Permission.none
    assert permissions_.pull_requests_ == ast.Permission.none


def test_jobs_context_builds():
    workflow_string = """
    on: push
    jobs:
      stale:
        runs-on: ubuntu-latest

        outputs:
          stale_output: ${{ steps.one.outputs.closed-issues-prs }}

        steps:
          - id: one
            uses: actions/stale@v9

    """  # TODO check if output reference is correct
    workflow_out, problems = parse_workflow_string(workflow_string)
    jobs_context = workflow_out.contexts.jobs
    assert isinstance(jobs_context, contexts.JobsContext)
    jobs_context_stale = jobs_context.children_['stale']
    assert isinstance(jobs_context_stale, contexts.JobVarContext)
    jobs_context_stale_outputs = jobs_context_stale.outputs
    assert isinstance(jobs_context_stale_outputs, contexts.OutputsContext)
    stale_output = jobs_context_stale_outputs.children_['stale_output']
    assert stale_output is not None
    assert isinstance(stale_output, contexts.ContextType)


def test_job_context_builds():
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
          - run: |
              echo "Redis available on 127.0.0.1:${{ job.services.redis.ports['6379'] }}"
              echo "Nginx available on 127.0.0.1:${{ job.services.nginx.ports['80'] }}"

    """
    workflow_out, problems = parse_workflow_string(workflow_string)
    job_context = workflow_out.jobs_['job'].contexts.job
    assert isinstance(job_context, contexts.JobContext)


def test_strategy():
    workflow_string = """
    on: push
    jobs:
      example_matrix:
        strategy:
          matrix:
            os: [windows-latest, ubuntu-latest]
            node: [14, 16]
            include:
              - os: windows-latest
                node: 16
                npm: 6
          fail-fast: true
          max-parallel: 6
        runs-on: ${{ matrix.os }}
        steps:
          - uses: actions/setup-node@v4
            with:
              node-version: ${{ matrix.node }}
          - if: ${{ matrix.npm }}
            run: npm install -g npm@${{ matrix.npm }}
          - run: npm --version
    """
    workflow_out, problems = parse_workflow_string(workflow_string)
    assert problems.problems == []

    strategy = workflow_out.jobs_['example_matrix'].strategy_
    assert strategy is not None
    assert strategy.fail_fast_ is True
    assert strategy.max_parallel_ == 6

    # Expected combinations:
    # {os: windows-latest, node: 14}
    # {os: windows-latest, node: 16, npm: 6} (from include)
    # {os: ubuntu-latest, node: 14}
    # {os: ubuntu-latest, node: 16}

    combinations = strategy.combinations
    assert len(combinations) == 4

    expected_combinations = [
        {'os': 'windows-latest', 'node': '14'},
        {'os': 'windows-latest', 'node': '16', 'npm': '6'},
        {'os': 'ubuntu-latest', 'node': '14'},
        {'os': 'ubuntu-latest', 'node': '16'},
    ]

    # Convert ast.String in combinations to simple dicts for easier comparison
    parsed_combinations = []
    for combo_dict in combinations:
        parsed_combo = {k.string: v.string for k, v in combo_dict.items()}
        parsed_combinations.append(parsed_combo)

    for expected_combo in expected_combinations:
        assert expected_combo in parsed_combinations, f"Expected combination {expected_combo} not found"

    # Check matrix context
    matrix_context = workflow_out.jobs_['example_matrix'].contexts.matrix
    assert matrix_context is not None
    assert 'os' in matrix_context.children_
    assert 'node' in matrix_context.children_
    assert 'npm' in matrix_context.children_
    assert matrix_context.children_['os'] == contexts.ContextType.string
    assert matrix_context.children_['node'] == contexts.ContextType.string
    assert matrix_context.children_['npm'] == contexts.ContextType.string


def test_job_runs_on_mapping_scalar_items():
    workflow_string = """
on: push
jobs:
  build:
    runs-on:
      labels: ubuntu-latest
      group: my-group
    steps:
      - name: Echo
        run: echo hi
"""
    workflow_out, problems = parse_workflow_string(workflow_string)
    runs_on = workflow_out.jobs_['build'].runs_on_
    assert problems.problems == []
    assert [l.string for l in runs_on.labels] == ['ubuntu-latest']
    assert [g.string for g in runs_on.group] == ['my-group']


def test_job_runs_on_single():
    workflow_string = """
on: push
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Echo
        run: echo hi
"""
    workflow_out, problems = parse_workflow_string(workflow_string)
    runs_on = workflow_out.jobs_['build'].runs_on_
    assert problems.problems == []
    assert [l.string for l in runs_on.labels] == ['ubuntu-latest']


def test_job_runs_on_list():
    workflow_string = """
on: push
jobs:
  build:
    runs-on: [ubuntu-latest, windows-latest]
    steps:
      - name: Echo
        run: echo hi
"""
    workflow_out, problems = parse_workflow_string(workflow_string)
    runs_on = workflow_out.jobs_['build'].runs_on_
    assert problems.problems == []
    assert [l.string for l in runs_on.labels] == ['ubuntu-latest', 'windows-latest']


def test_job_runs_on_unknown_key():
    workflow_string = """
on: push
jobs:
  build:
    runs-on:
      foo: bar
    steps:
      - name: Echo
        run: echo hi
"""
    workflow_out, problems = parse_workflow_string(workflow_string)
    runs_on = workflow_out.jobs_['build'].runs_on_
    assert runs_on is not None
    # Unknown key should produce an error but still return RunsOn
    assert any(p.desc == "Unknown key in 'runs-on': foo" for p in problems.problems)
    assert runs_on.labels == []
    assert runs_on.group == []


def test_job_runs_on_mapping_list_with_invalid_items():
    workflow_string = """
on: push
jobs:
  build:
    runs-on:
      labels: [ubuntu-latest, 123, windows-latest]
      group: true
    steps:
      - name: Echo
        run: echo hi
"""
    workflow_out, problems = parse_workflow_string(workflow_string)
    runs_on = workflow_out.jobs_['build'].runs_on_
    # Two errors: one for invalid list item 123, one for invalid scalar for group
    assert len(problems.problems) == 2
    descs = [p.desc for p in problems.problems]
    assert "Invalid item in 'runs-on' 'labels': 123" in descs
    assert "Invalid item in 'runs-on' 'group': True" in descs


def test_job_environment_string():
    workflow_string = """
on: push
jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: production
    steps:
      - name: Do something
        run: echo done
"""
    workflow_out, problems = parse_workflow_string(workflow_string)
    environment = workflow_out.jobs_['deploy'].environment_
    assert problems.problems == []
    assert environment is not None
    assert environment.name_.string == 'production'
    assert environment.url_ is None


def test_job_environment_mapping():
    workflow_string = """
on: push
jobs:
  deploy:
    runs-on: ubuntu-latest
    environment:
      name: staging
      url: https://example.com
    steps:
      - name: Do something
        run: echo done
"""
    workflow_out, problems = parse_workflow_string(workflow_string)
    environment = workflow_out.jobs_['deploy'].environment_
    assert problems.problems == []
    assert environment is not None
    assert environment.name_.string == 'staging'
    assert environment.url_.string == 'https://example.com'


def test_job_environment_invalid_scalar():
    workflow_string = """
on: push
jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: 123
    steps:
      - name: Do something
        run: echo done
"""
    workflow_out, problems = parse_workflow_string(workflow_string)
    assert workflow_out.jobs_['deploy'].environment_ is None
    assert len(problems.problems) == 1
    descs = [p.desc for p in problems.problems]
    assert "Invalid 'environment' value: '123'" in descs


def test_job_environment_invalid_name_mapping():
    workflow_string = """
on: push
jobs:
  deploy:
    runs-on: ubuntu-latest
    environment:
      name: 123
      url: https://example.com
    steps:
      - name: Do something
        run: echo done
"""
    workflow_out, problems = parse_workflow_string(workflow_string)
    assert workflow_out.jobs_['deploy'].environment_ is None
    descs = [p.desc for p in problems.problems]
    assert "Invalid 'environment' 'name': '123'" in descs


def test_job_environment_invalid_url_mapping():
    workflow_string = """
on: push
jobs:
  deploy:
    runs-on: ubuntu-latest
    environment:
      name: staging
      url: 456
    steps:
      - name: Do something
        run: echo done
"""
    workflow_out, problems = parse_workflow_string(workflow_string)
    assert workflow_out.jobs_['deploy'].environment_ is None
    descs = [p.desc for p in problems.problems]
    assert "Invalid 'environment' 'url': '456'" in descs
