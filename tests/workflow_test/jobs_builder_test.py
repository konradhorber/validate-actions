from tests.helper import parse_workflow_string
from validate_actions.workflow import ast


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
