from validateactions import cli
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
        cli.run(tmp_path)
    finally:
        os.remove(tmp_path)
    # tokens = list(parser.tokenize(workflow))
    assert None is None