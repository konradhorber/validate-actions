import os
import tempfile
from pathlib import Path

import requests

from tests.helper import parse_workflow_string
from validate_actions import Problem, ProblemLevel, fixer, rules


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
    rule = rules.JobsStepsUses(workflow, False, None)
    gen = rule.check()
    result = list(gen)
    assert len(result) == 1
    assert isinstance(result[0], Problem)
    assert result[0].rule == "jobs-steps-uses"
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
        uses: 8398a7/action-slack@v3
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
        uses: 8398a7/action-slack@v3
        with:
          wrong_input: 'test'
          status: 'test'
"""
    workflow, problems = parse_workflow_string(workflow_string)
    rule = rules.JobsStepsUses(workflow, False, None)
    gen = rule.check()
    result = list(gen)
    assert len(result) == 1
    assert isinstance(result[0], Problem)
    assert result[0].rule == "jobs-steps-uses"
    assert result[0].pos.line == 7
    assert result[0].desc == "8398a7/action-slack@v3 uses unknown input: wrong_input"


def test_uses_non_existent_input_second():
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
    rule = rules.JobsStepsUses(workflow, False, None)
    gen = rule.check()
    result = list(gen)
    assert len(result) == 1
    assert isinstance(result[0], Problem)
    assert result[0].rule == "jobs-steps-uses"
    assert result[0].pos.line == 7
    assert result[0].desc == "8398a7/action-slack@v3 uses unknown input: wrong_input"


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
    url = "https://api.github.com/repos/actions/checkout/tags"
    token = os.getenv("GITHUB_TOKEN")
    header = {}
    if token:
        header = {"Authorization": f"token {token}"}
    try:
        response = requests.get(url, headers=header)
    except requests.RequestException as e:
        assert False, f"Request error for {url}: {e}"

    version = response.json()[0]["name"]
    workflow_string_with_version = workflow_string_without_version.replace(
        "uses: actions/checkout", f"uses: actions/checkout@{version}"
    )

    temp_file_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w+", delete=False, suffix=".yml", encoding="utf-8"
        ) as f:
            f.write(workflow_string_without_version)
            temp_file_path = Path(f.name)

        workflow_obj, initial_problems = parse_workflow_string(workflow_string_without_version)
        workflow_obj.path = temp_file_path
        fix = fixer.BaseFixer(temp_file_path)
        rule = rules.JobsStepsUses(workflow_obj, True, fix)
        problems_after_fix = list(rule.check())
        # Assert that the problem was fixed and non problem is reported for this specific issue
        assert len(problems_after_fix) == 1
        assert problems_after_fix[0].level == ProblemLevel.NON  # 1 Non problem after fix
        fixed_content = temp_file_path.read_text(encoding="utf-8")
        assert fixed_content.strip() == workflow_string_with_version.strip()
    finally:
        if temp_file_path:
            temp_file_path.unlink(missing_ok=True)


def throws_single_error(workflow_string: str):
    workflow, problems = parse_workflow_string(workflow_string)
    fixy = fixer.BaseFixer(Path(tempfile.gettempdir()))
    rule = rules.JobsStepsUses(workflow, False, fixy)
    gen = rule.check()
    result = list(gen)
    assert len(result) == 1
    assert isinstance(result[0], Problem)
    assert result[0].rule == "jobs-steps-uses"


def throws_no_error(workflow_string: str):
    workflow, problems = parse_workflow_string(workflow_string)
    fixy = fixer.BaseFixer(Path(tempfile.gettempdir()))
    rule = rules.JobsStepsUses(workflow, False, fixy)
    gen = rule.check()
    result = list(gen)
    assert result == []


# region outdated version tests
def test_outdated_major_version_v3_when_v4_available():
    """Test warning for outdated major version: v3 when v4.x.x is current"""
    workflow_string = """
name: test
on: push
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v3
"""
    workflow, problems = parse_workflow_string(workflow_string)
    rule = rules.JobsStepsUses(workflow, False, None)
    gen = rule.check()
    result = list(gen)

    # Should find one outdated version warning
    outdated_warnings = [p for p in result if "outdated" in p.desc.lower()]
    assert len(outdated_warnings) == 1
    assert outdated_warnings[0].level == ProblemLevel.WAR
    assert outdated_warnings[0].rule == "jobs-steps-uses"
    assert "v3" in outdated_warnings[0].desc


def test_outdated_minor_version_v4_1_when_v4_2_available():
    """Test warning for outdated minor: v4.1 when v4.2.x is current"""
    workflow_string = """
name: test
on: push
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4.1
"""
    workflow, problems = parse_workflow_string(workflow_string)
    rule = rules.JobsStepsUses(workflow, False, None)
    gen = rule.check()
    result = list(gen)

    # Should find one outdated version warning
    outdated_warnings = [p for p in result if "outdated" in p.desc.lower()]
    assert len(outdated_warnings) == 1
    assert outdated_warnings[0].level == ProblemLevel.WAR
    assert outdated_warnings[0].rule == "jobs-steps-uses"
    assert "v4.1" in outdated_warnings[0].desc


def test_outdated_patch_version_v4_2_1_when_v4_2_2_available():
    """Test warning for outdated patch: v4.2.1 when v4.2.2 is current"""
    workflow_string = """
name: test
on: push
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4.2.1
"""
    workflow, problems = parse_workflow_string(workflow_string)
    rule = rules.JobsStepsUses(workflow, False, None)
    gen = rule.check()
    result = list(gen)

    # Should find one outdated version warning
    outdated_warnings = [p for p in result if "outdated" in p.desc.lower()]
    assert len(outdated_warnings) == 1
    assert outdated_warnings[0].level == ProblemLevel.WAR
    assert outdated_warnings[0].rule == "jobs-steps-uses"
    assert "v4.2.1" in outdated_warnings[0].desc


def test_v4_resolves_to_latest_v4_x_x():
    """Test that v4 uses latest v4.x.x (e.g., v4.2.2), not v4.0.0 - should not warn"""
    workflow_string = """
name: test
on: push
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4
"""
    workflow, problems = parse_workflow_string(workflow_string)
    rule = rules.JobsStepsUses(workflow, False, None)
    gen = rule.check()
    result = list(gen)

    # Should NOT find outdated version warnings because v4 resolves to latest v4.x.x
    outdated_warnings = [p for p in result if "outdated" in p.desc.lower()]
    assert len(outdated_warnings) == 0


def test_commit_sha_mapped_to_version():
    """Test commit SHA gets mapped to its version and compared"""
    workflow_string = """
name: test
on: push
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@8e5e7e5ab8b370d6c329ec480221332ada57f0ab
"""
    workflow, problems = parse_workflow_string(workflow_string)
    rule = rules.JobsStepsUses(workflow, False, None)
    gen = rule.check()
    result = list(gen)

    # Should find warning with SHA and version info
    outdated_warnings = [
        p for p in result if "commit" in p.desc.lower() or "sha" in p.desc.lower()
    ]
    assert len(outdated_warnings) == 1
    assert outdated_warnings[0].level == ProblemLevel.WAR
    assert outdated_warnings[0].rule == "jobs-steps-uses"
    assert "8e5e7e5ab8b370d6c329ec480221332ada57f0ab" in outdated_warnings[0].desc


def test_current_latest_version_no_warning():
    """Test that using the latest version doesn't trigger warning"""
    workflow_string = """
name: test
on: push
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4.2.2
"""
    workflow, problems = parse_workflow_string(workflow_string)
    rule = rules.JobsStepsUses(workflow, False, None)
    gen = rule.check()
    result = list(gen)

    # Should not find any outdated version warnings
    outdated_warnings = [p for p in result if "outdated" in p.desc.lower()]
    assert len(outdated_warnings) == 0


def test_action_without_version_ignored_by_outdated_check():
    """Test that actions without version specs are ignored by outdated check"""
    workflow_string = """
name: test
on: push
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout
"""
    workflow, problems = parse_workflow_string(workflow_string)
    rule = rules.JobsStepsUses(workflow, False, None)
    gen = rule.check()
    result = list(gen)

    # Should find missing version spec warning but no outdated version warning
    version_spec_warnings = [p for p in result if "recommended @version" in p.desc]
    outdated_warnings = [p for p in result if "outdated" in p.desc.lower()]

    assert len(version_spec_warnings) == 1
    assert len(outdated_warnings) == 0


def test_multiple_outdated_actions():
    """Test multiple outdated actions in same workflow"""
    workflow_string = """
name: test
on: push
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v3
      - name: Setup Node  
        uses: actions/setup-node@v3
      - name: Cache
        uses: actions/cache@v2
"""
    workflow, problems = parse_workflow_string(workflow_string)
    rule = rules.JobsStepsUses(workflow, False, None)
    gen = rule.check()
    result = list(gen)

    # Should find multiple outdated version warnings
    outdated_warnings = [p for p in result if "outdated" in p.desc.lower()]
    assert len(outdated_warnings) >= 3


def test_unknown_action_graceful_handling():
    """Test graceful handling of unknown/private actions"""
    workflow_string = """
name: test
on: push
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Private Action
        uses: private-org/private-action@v1.0.0
"""
    workflow, problems = parse_workflow_string(workflow_string)
    rule = rules.JobsStepsUses(workflow, False, None)
    gen = rule.check()
    result = list(gen)

    # Should handle gracefully and not crash
    # May produce warning about unable to fetch metadata but shouldn't crash
    assert True  # Test that it doesn't crash


def test_fix_outdated_version():
    """Test auto-fix updates outdated version to latest"""
    workflow_string_outdated = """
    on: push
    jobs:
      build:
        runs-on: ubuntu-latest
        steps:
          - uses: actions/checkout@v3
    """

    temp_file_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w+", delete=False, suffix=".yml", encoding="utf-8"
        ) as f:
            f.write(workflow_string_outdated)
            temp_file_path = Path(f.name)

        workflow_obj, initial_problems = parse_workflow_string(workflow_string_outdated)
        workflow_obj.path = temp_file_path
        fix = fixer.BaseFixer(temp_file_path)
        rule = rules.JobsStepsUses(workflow_obj, True, fix)
        problems_after_fix = list(rule.check())

        # Should have at least one NON problem after fix
        fixed_problems = [p for p in problems_after_fix if p.level == ProblemLevel.NON]
        assert len(fixed_problems) >= 1

        # Content should be updated to latest version
        fixed_content = temp_file_path.read_text(encoding="utf-8")
        assert "@v3" not in fixed_content
        # Should have latest version (will be actual latest when implemented)
    finally:
        if temp_file_path:
            temp_file_path.unlink(missing_ok=True)


# endregion outdated version tests
