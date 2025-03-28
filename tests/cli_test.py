from validate_actions import cli, linter
import tempfile
import os

def test_run():
    workflow = """name: test
on:
  pus:
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
          unknown_input: 'test'
"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp:
        tmp.write(workflow)
        tmp_path = tmp.name 

    try:
        with open(tmp_path, 'r') as f:
            problems = linter.run(f)
    finally:
        os.remove(tmp_path)
    
    sorted_problems = sorted(problems, key=lambda x: (x.line, x.column))

    assert len(sorted_problems) == 5
    rule_event = 'event-trigger'
    rule_input = 'jobs-steps-uses'
    assert sorted_problems[0].rule == rule_event
    assert sorted_problems[1].rule == rule_event
    assert sorted_problems[2].rule == rule_input
    assert sorted_problems[2].level == 'warning'
    assert sorted_problems[3].rule == rule_input
    assert sorted_problems[4].rule == rule_input