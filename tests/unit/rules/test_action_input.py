import tempfile
from pathlib import Path

from tests.conftest import parse_workflow_string
from validate_actions import Problem
from validate_actions.globals import fixer
from validate_actions.globals.fixer import NoFixer
from validate_actions.rules.action_input import ActionInput


class TestActionInput:
    # region required inputs
    def test_required_input_but_no_with(self):
        workflow = """
    name: test
    jobs:
      build:
        runs-on: ubuntu-latest
        steps:
          - name: Notify Slack
            uses: 8398a7/action-slack@v3
    """
        self.throws_single_error(workflow)

    def test_required_input_correct_with(self):
        workflow = """
    name: test
    jobs:
      build:
        runs-on: ubuntu-latest
        steps:
          - name: Notify Slack
            uses: 8398a7/action-slack@v3
            with:
              status: 'test'
    """
        self.throws_no_error(workflow)

    def test_required_input_but_wrong_with_ending_directly(self):
        workflow = """
    name: test
    jobs:
      build:
        runs-on: ubuntu-latest
        steps:
          - name: Notify Slack
            uses: 8398a7/action-slack@v3
            with:
              fields: 'test'
    """
        self.throws_single_error(workflow)

    def test_required_input_but_wrong_with_block_continues(self):
        workflow = """
    name: test
    jobs:
      build:
        runs-on: ubuntu-latest
        steps:
          - name: Notify Slack
            uses: 8398a7/action-slack@v3
            with:
              fields: 'test'
          - run: npm install
    """
        self.throws_single_error(workflow)

    def test_required_input_correct_with_multiple_inputs(self):
        workflow = """
    name: test
    jobs:
      build:
        runs-on: ubuntu-latest
        steps:
          - name: Notify Slack
            uses: 8398a7/action-slack@v3
            with:
              fields: 'test'
              status: 'correct'
    """
        self.throws_no_error(workflow)

    def test_required_input_but_wrong_multiple_inputs(self):
        workflow = """
    name: test
    jobs:
      build:
        runs-on: ubuntu-latest
        steps:
          - name: Notify Slack
            uses: 8398a7/action-slack@v3
            with:
              fields: 'test'
              custom_payload: 'test'
    """
        self.throws_single_error(workflow)

    # endregion required inputs

    # region all inputs
    def test_uses_existent_optional_input(self):
        workflow = """
    name: test
    jobs:
      build:
        runs-on: ubuntu-latest
        steps:
          - name: Notify Slack
            uses: 8398a7/action-slack@v3
            with:
              status: 'test'
    """
        self.throws_no_error(workflow)

    def test_uses_non_existent_input_first(self):
        workflow_string = """
    name: test
    jobs:
      build:
        runs-on: ubuntu-latest
        steps:
          - name: Notify Slack
            uses: 8398a7/action-slack@v3
            with:
              wrong_input: 'test'
              status: 'test'
    """
        workflow, problems = parse_workflow_string(workflow_string)
        rule = ActionInput(workflow, NoFixer())
        gen = rule.check()
        result = list(gen)
        assert len(result) == 1
        assert isinstance(result[0], Problem)
        assert result[0].rule == "action-input"
        assert result[0].pos.line == 7
        assert result[0].desc == "8398a7/action-slack@v3 uses unknown input: wrong_input"

    def test_uses_non_existent_input_second(self):
        workflow_string = """
    name: test
    jobs:
      build:
        runs-on: ubuntu-latest
        steps:
          - name: Notify Slack
            uses: 8398a7/action-slack@v3
            with:
              status: 'test'
              wrong_input: 'test'
    """
        workflow, problems = parse_workflow_string(workflow_string)
        rule = ActionInput(workflow, NoFixer())
        gen = rule.check()
        result = list(gen)
        assert len(result) == 1
        assert isinstance(result[0], Problem)
        assert result[0].rule == "action-input"
        assert result[0].pos.line == 7
        assert result[0].desc == "8398a7/action-slack@v3 uses unknown input: wrong_input"

    # endregion all inputs

    def throws_single_error(self, workflow_string: str):
        workflow, problems = parse_workflow_string(workflow_string)
        fixy = fixer.BaseFixer(Path(tempfile.gettempdir()))
        rule = ActionInput(workflow, fixy)
        gen = rule.check()
        result = list(gen)
        assert len(result) == 1
        assert isinstance(result[0], Problem)
        assert result[0].rule == "action-input"

    def throws_no_error(self, workflow_string: str):
        workflow, problems = parse_workflow_string(workflow_string)
        fixy = fixer.BaseFixer(Path(tempfile.gettempdir()))
        rule = ActionInput(workflow, fixy)
        gen = rule.check()
        result = list(gen)
        assert result == []
