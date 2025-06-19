from tests.helper import parse_workflow_string
from validate_actions.workflow import ast


def test_workflow_env():
    workflow_string = """
on: push
env:
  GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
  FIRST_NAME: Mona
  LAST_NAME: Octocat
jobs:
  build:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v4
"""
    workflow_out, problems = parse_workflow_string(workflow_string)
    env_ = workflow_out.env_
    assert len(problems.problems) == 0
    assert env_.get('GITHUB_TOKEN').string == '${{ secrets.GITHUB_TOKEN }}'
    assert env_.get('FIRST_NAME').string == 'Mona'
    assert env_.get('LAST_NAME').string == 'Octocat'


def test_workflow_permissions():
    workflow_string = """
name: "My workflow"

on: [ push ]

permissions: read-all

jobs:
  build:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v4
"""
    workflow_out, problems = parse_workflow_string(workflow_string)
    permissions_ = workflow_out.permissions_
    assert permissions_.issues_ == ast.Permission.read
    assert permissions_.pull_requests_ == ast.Permission.read
    assert permissions_.id_token_ == ast.Permission.read
    assert permissions_.contents_ == ast.Permission.read


# Integration tests for defaults using parse_workflow_string
def test_workflow_defaults_shell():
    workflow_string = """
on: push
defaults:
  run:
    shell: bash
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Echo
        run: echo hello
"""
    workflow_out, problems = parse_workflow_string(workflow_string)
    defaults = workflow_out.defaults_
    assert len(problems.problems) == 0
    assert defaults is not None
    assert defaults.shell_.value == "bash"
    assert defaults.working_directory_ is None


def test_workflow_defaults_working_directory():
    workflow_string = """
on: push
defaults:
  run:
    working-directory: /tmp
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Echo
        run: echo hello
"""
    workflow_out, problems = parse_workflow_string(workflow_string)
    defaults = workflow_out.defaults_
    assert len(problems.problems) == 0
    assert defaults is not None
    assert defaults.shell_ is None
    assert defaults.working_directory_.string == "/tmp"


def test_workflow_defaults_shell_and_working_directory():
    workflow_string = """
on: push
defaults:
  run:
    shell: bash
    working-directory: /tmp
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Echo
        run: echo hello
"""
    workflow_out, problems = parse_workflow_string(workflow_string)
    defaults = workflow_out.defaults_
    assert len(problems.problems) == 0
    assert defaults is not None
    assert defaults.shell_.value == "bash"
    assert defaults.working_directory_.string == "/tmp"


def test_workflow_defaults_invalid_structure():
    workflow_string = """
on: push
defaults: not_a_map
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Echo
        run: echo hello
"""
    workflow_out, problems = parse_workflow_string(workflow_string)
    assert workflow_out.defaults_ is None
    assert any(p.desc.startswith("Invalid 'defaults:'") for p in problems.problems)


def test_workflow_defaults_invalid_shell():
    workflow_string = """
on: push
defaults:
  run:
    shell: fish
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Echo
        run: echo hello
"""
    workflow_out, problems = parse_workflow_string(workflow_string)
    # Invalid shell 'fish' should produce an error and no defaults
    assert workflow_out.defaults_ is None
    assert any(p.desc == "Invalid shell: fish" for p in problems.problems)


def test_workflow_concurrency_minimal_group():
    workflow_string = """
on: push
concurrency:
  group: my-group
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Test
        run: echo hi
"""
    workflow_out, problems = parse_workflow_string(workflow_string)
    assert len(problems.problems) == 0
    assert workflow_out.concurrency_ is not None
    assert workflow_out.concurrency_.group_.string == "my-group"
    assert workflow_out.concurrency_.cancel_in_progress_ is None


def test_workflow_concurrency_with_cancel_true():
    workflow_string = """
on: push
concurrency:
  group: grp-cancel
  cancel-in-progress: true
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Test
        run: echo hi
"""
    workflow_out, problems = parse_workflow_string(workflow_string)
    assert len(problems.problems) == 0
    assert workflow_out.concurrency_ is not None
    assert workflow_out.concurrency_.group_.string == "grp-cancel"
    assert workflow_out.concurrency_.cancel_in_progress_ is True


def test_workflow_concurrency_missing_group():
    workflow_string = """
on: push
concurrency:
  cancel-in-progress: true
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Test
        run: echo hi
"""
    workflow_out, problems = parse_workflow_string(workflow_string)
    assert workflow_out.concurrency_ is None
    assert any(p.desc == "Concurrency must define 'group'" for p in problems.problems)
