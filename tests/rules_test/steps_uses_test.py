import tempfile
from pathlib import Path

import requests

from tests.helper import parse_workflow_string
from validate_actions import Problem, ProblemLevel, rules


# with
def test_unknown_action_throws_warning():
    workflow_string = """
name: test
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Notify Slack
        uses: action/is-unknown@vtest
        with:
          unknown_input: 'test'
"""
    workflow, problems = parse_workflow_string(workflow_string)
    gen = rules.JobsStepsUses.check(workflow, False)
    result = list(gen)
    assert len(result) == 1
    assert isinstance(result[0], Problem)
    assert result[0].rule == 'jobs-steps-uses'
    assert result[0].level == ProblemLevel.WAR


# region required inputs
def test_required_input_but_no_with():
    workflow = """
name: test
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Notify Slack
        uses: 8398a7/action-slack@v3
"""
    throws_single_error(workflow)


def test_required_input_correct_with():
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
    throws_no_error(workflow)


def test_required_input_but_wrong_with_ending_directly():
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
    throws_single_error(workflow)


def test_required_input_but_wrong_with_block_continues():
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
    throws_single_error(workflow)


def test_required_input_correct_with_multiple_inputs():
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
    throws_no_error(workflow)


def test_required_input_but_wrong_multiple_inputs():
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
    throws_single_error(workflow)
# endregion required inputs


# region all inputs
def test_uses_existent_optional_input():
    workflow = """
name: test
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Notify Slack
        uses: 8398a7/action-slack@v2
        with:
          status: 'test'
"""
    throws_no_error(workflow)


def test_uses_non_existent_input_first():
    workflow_string = """
name: test
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Notify Slack
        uses: 8398a7/action-slack@v2
        with:
          wrong_input: 'test'
          status: 'test'
"""
    workflow, problems = parse_workflow_string(workflow_string)
    gen = rules.JobsStepsUses.check(workflow, False)
    result = list(gen)
    assert len(result) == 1
    assert isinstance(result[0], Problem)
    assert result[0].rule == 'jobs-steps-uses'
    assert result[0].pos.line == 7
    assert result[0].desc == "8398a7/action-slack@v2 uses unknown input: wrong_input"


def test_uses_non_existent_input_second():
    workflow_string = """
name: test
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Notify Slack
        uses: 8398a7/action-slack@v2
        with:
          status: 'test'
          wrong_input: 'test'
"""
    workflow, problems = parse_workflow_string(workflow_string)
    gen = rules.JobsStepsUses.check(workflow, False)
    result = list(gen)
    assert len(result) == 1
    assert isinstance(result[0], Problem)
    assert result[0].rule == 'jobs-steps-uses'
    assert result[0].pos.line == 7
    assert result[0].desc == "8398a7/action-slack@v2 uses unknown input: wrong_input"

# endregion all inputs


def test_fix_missing_version_spec(tmp_path, monkeypatch):
    workflow_string_without_version = """
    on: push
    jobs:
      build:
        runs-on: ubuntu-latest
        steps:
          - uses: actions/checkout
    """
    url = 'https://api.github.com/repos/actions/checkout/tags'
    try:
        response = requests.get(url)
    except requests.RequestException as e:
        assert False, f"Request error for {url}: {e}"

    version = response.json()[0]['name']
    workflow_string_with_version = workflow_string_without_version.replace(
        'uses: actions/checkout',
        f'uses: actions/checkout@{version}'
    )

    temp_file_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode='w+', delete=False, suffix='.yml', encoding='utf-8'
        ) as f:
            f.write(workflow_string_without_version)
            temp_file_path = Path(f.name)

        workflow_obj, initial_problems = parse_workflow_string(workflow_string_without_version)
        workflow_obj.path = temp_file_path
        problems_after_fix = list(rules.JobsStepsUses.check(workflow_obj, fix=True))
        # Assert that the problem was fixed and non problem is reported for this specific issue
        assert len(problems_after_fix) == 1
        assert problems_after_fix[0].level == ProblemLevel.NON  # 1 Non problem after fix
        fixed_content = temp_file_path.read_text(encoding='utf-8')
        assert fixed_content.strip() == workflow_string_with_version.strip()
    finally:
        if temp_file_path:
            temp_file_path.unlink(missing_ok=True)


def throws_single_error(workflow_string: str):
    workflow, problems = parse_workflow_string(workflow_string)
    gen = rules.JobsStepsUses.check(workflow, False)
    result = list(gen)
    assert len(result) == 1
    assert isinstance(result[0], Problem)
    assert result[0].rule == 'jobs-steps-uses'


def throws_no_error(workflow_string: str):
    workflow, problems = parse_workflow_string(workflow_string)
    gen = rules.JobsStepsUses.check(workflow, False)
    result = list(gen)
    assert result == []
