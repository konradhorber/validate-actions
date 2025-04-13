from tests.helper import parse_workflow_string


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
    assert problems == []
    assert env_.get('GITHUB_TOKEN').string == '${{ secrets.GITHUB_TOKEN }}'
    assert env_.get('FIRST_NAME').string == 'Mona'
    assert env_.get('LAST_NAME').string == 'Octocat'
