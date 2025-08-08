import os
import tempfile
from pathlib import Path

from validate_actions import ProblemLevel


class TestCLI:
    def test_run(self):
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
        with tempfile.NamedTemporaryFile(suffix=".yml", mode="w+", delete=False) as temp_file:
            temp_file.write(workflow_string)
            temp_file_path = Path(temp_file.name)

        try:
            from validate_actions.globals.fixer import NoFixer
            from validate_actions.globals.web_fetcher import DefaultWebFetcher
            from validate_actions.pipeline import DefaultPipeline

            web_fetcher = DefaultWebFetcher(github_token=os.getenv("GH_TOKEN"))
            pipeline = DefaultPipeline(web_fetcher, NoFixer())
            problems = pipeline.process(temp_file_path)
        finally:
            temp_file_path.unlink(missing_ok=True)

        problems.sort()
        problems_list = problems.problems

        assert len(problems_list) == 4
        rule_event = "events-syntax-error"
        rule_input = "jobs-steps-uses"
        assert problems_list[0].rule == rule_event
        assert problems_list[1].rule == rule_input
        assert problems_list[1].level == ProblemLevel.WAR
        assert problems_list[2].rule == rule_input
        assert problems_list[3].rule == rule_input
