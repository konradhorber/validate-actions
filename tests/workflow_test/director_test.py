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
