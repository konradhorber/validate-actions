import tempfile
from pathlib import Path

from validate_actions import ProblemLevel, validator


def test_run():
    workflow_string = """name: test
on:
  push:
    branches: [ $default-branch ]
  pullrequest:
    branches: [ $default-branch ]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Notify Slack
        uses: 8398a7/action-slack
        with:
          unknown_input: 'test'
      - name: Notify Slack
        uses: 8398a7/action-slack@v3
        with:
          status: 'test'
"""
    with tempfile.NamedTemporaryFile(
        suffix='.yml', mode='w+', delete=False
    ) as temp_file:
        temp_file.write(workflow_string)
        temp_file_path = Path(temp_file.name)

    try:
        problems = validator.Validator.run(temp_file_path)
    finally:
        temp_file_path.unlink(missing_ok=True)

    problems.sort()
    problems_list = problems.problems

    assert len(problems_list) == 4
    rule_event = 'events-syntax-error'
    rule_input = 'jobs-steps-uses'
    assert problems_list[0].rule == rule_event
    assert problems_list[1].rule == rule_input
    assert problems_list[1].level == ProblemLevel.WAR
    assert problems_list[2].rule == rule_input
    assert problems_list[3].rule == rule_input
