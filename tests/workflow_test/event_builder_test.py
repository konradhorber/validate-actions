import validate_actions
from tests.helper import parse_workflow_string


def test_build_event_schedule_single():
    workflow_string = """
on:
  schedule:
    - cron: '0 0 * * *'
"""
    workflow, problems = parse_workflow_string(workflow_string)
    cron_event = workflow.on_[0]
    assert isinstance(cron_event, validate_actions.workflow.ScheduleEvent)
    assert cron_event.cron_[0].string == "0 0 * * *"


def test_build_event_schedule_list():
    workflow_string = """
on:
  schedule:
    - cron: '0 0 * * *'
    - cron: '0 1 * * *'
"""
    workflow, problems = parse_workflow_string(workflow_string)
    cron_event = workflow.on_[0]
    assert isinstance(cron_event, validate_actions.workflow.ScheduleEvent)
    assert cron_event.cron_[0].string == "0 0 * * *"
    assert cron_event.cron_[1].string == "0 1 * * *"


def test_build_event_pull_request():
    workflow_string = """
on:
  pull_request:
    branches: [main, dev]
    paths:
      - src/**
"""
    workflow, problems = parse_workflow_string(workflow_string)
    pull_request_event = workflow.on_[0]
    assert isinstance(pull_request_event, validate_actions.workflow.PathsBranchesFilterEvent)
    assert pull_request_event.branches_[0].string == "main"
    assert pull_request_event.branches_[1].string == "dev"
    assert pull_request_event.paths_[0].string == "src/**"


def test_build_event_push():
    workflow_string = """
on:
  push:
    branches:
      - main
    tags:
      - v2
      - v1.*
"""
    workflow, problems = parse_workflow_string(workflow_string)
    push_event = workflow.on_[0]
    assert isinstance(push_event, validate_actions.workflow.TagsPathsBranchesFilterEvent)
    assert push_event.branches_[0].string == "main"
    assert len(push_event.tags_) == 2
    assert push_event.tags_[0].string == "v2"
    assert push_event.tags_[1].string == "v1.*"


def test_build_event_workflow_call():
    workflow_string = """
on:
  workflow_call:
    inputs:
      username:
        description: 'A username passed from the caller workflow'
        default: 'john-doe'
        required: true
        type: string
      time:
        description: 'A time passed from the caller workflow'
    outputs:
      workflow_output1:
        value: ${{ jobs.my_job.outputs.job_output1 }}
      workflow_output2:
        description: "The second job output"
        value: ${{ jobs.my_job.outputs.job_output2 }}
    secrets:
      access-token:
        description: 'A token passed from the caller workflow'
        required: false
"""
    workflow, problems = parse_workflow_string(workflow_string)
    workflow_call_event = workflow.on_[0]
    assert isinstance(workflow_call_event, validate_actions.workflow.WorkflowCallEvent)
    inputs = workflow_call_event.inputs_
    outputs = workflow_call_event.outputs_
    secrets = workflow_call_event.secrets_
    assert workflow_call_event.id.string == "workflow_call"

    assert len(inputs) == 1  # time lacks required 'type' and shouldn't be in
    assert inputs[0].id.string == "username"
    expected_desc = "A username passed from the caller workflow"
    assert inputs[0].description_.string == expected_desc
    assert inputs[0].default_.string == "john-doe"
    assert inputs[0].required_ is True
    assert inputs[0].type_ == (validate_actions.workflow.WorkflowCallInputType.string)

    assert len(outputs) == 2
    assert outputs[0].id.string == "workflow_output1"
    assert outputs[0].value_.string == "${{ jobs.my_job.outputs.job_output1 }}"
    assert outputs[1].id.string == "workflow_output2"
    assert outputs[1].description_.string == "The second job output"
    assert outputs[1].value_.string == "${{ jobs.my_job.outputs.job_output2 }}"

    assert len(secrets) == 1
    assert secrets[0].id.string == "access-token"
    expected_desc = "A token passed from the caller workflow"

    assert secrets[0].description_.string == expected_desc
    assert secrets[0].required_ is False


def test_build_event_workflow_run():
    workflow_string = """
on:
  workflow_run:
    workflows: [main]
    types:
      - completed
    branches-ignore:
      - main
      - dev
"""
    workflow, problems = parse_workflow_string(workflow_string)
    workflow_run_event = workflow.on_[0]
    assert isinstance(workflow_run_event, validate_actions.workflow.WorkflowRunEvent)
    assert workflow_run_event.id.string == "workflow_run"
    assert len(workflow_run_event.workflows_) == 1
    assert workflow_run_event.workflows_[0].string == "main"

    assert len(workflow_run_event.types_) == 1
    assert workflow_run_event.types_[0].string == "completed"

    assert len(workflow_run_event.branches_ignore_) == 2
    assert workflow_run_event.branches_ignore_[0].string == "main"
    assert workflow_run_event.branches_ignore_[1].string == "dev"


def test_build_event_workflow_dispatch():
    workflow_string = """
on:
  workflow_dispatch:
    inputs:
      logLevel:
        description: 'Log level'
        required: true
        default: 'warning'
        type: choice
        options:
          - info
          - warning
          - debug
      print_tags:
        description: 'True to print to STDOUT'
        required: true
        type: boolean
      tags:
        description: 'Test scenario tags'
        required: true
        type: string
      environment:
        description: 'Environment to run tests against'
        type: environment
        required: false
"""
    workflow, problems = parse_workflow_string(workflow_string)
    workflow_dispatch_event = workflow.on_[0]
    assert isinstance(workflow_dispatch_event, validate_actions.workflow.WorkflowDispatchEvent)
    assert workflow_dispatch_event.id.string == "workflow_dispatch"
    inputs = workflow_dispatch_event.inputs_
    assert len(inputs) == 4
    assert inputs[0].id.string == "logLevel"
    assert inputs[0].description_.string == "Log level"
    assert inputs[0].required_ is True
    assert inputs[0].default_.string == "warning"
    type_ = validate_actions.workflow.WorkflowDispatchInputType.choice
    assert inputs[0].type_ == type_
    assert len(inputs[0].options_) == 3
    assert inputs[0].options_[0].string == "info"
    assert inputs[0].options_[1].string == "warning"
    assert inputs[0].options_[2].string == "debug"
    assert inputs[1].id.string == "print_tags"
    assert inputs[1].description_.string == "True to print to STDOUT"
    assert inputs[1].required_ is True
    type_ = validate_actions.workflow.WorkflowDispatchInputType.boolean
    assert inputs[1].type_ == type_
    assert inputs[2].id.string == "tags"
    assert inputs[2].description_.string == "Test scenario tags"
    assert inputs[2].required_ is True
    type_ = validate_actions.workflow.WorkflowDispatchInputType.string
    assert inputs[2].type_ == type_
    assert inputs[3].id.string == "environment"
    assert inputs[3].description_.string == "Environment to run tests against"
    assert inputs[3].required_ is False
    type_ = validate_actions.workflow.WorkflowDispatchInputType.environment
    assert inputs[3].type_ == type_
    assert inputs[3].options_ is None


def test_no_on():
    workflow_string = """
name: test
"""
    workflow, problems = parse_workflow_string(workflow_string)
    problems = problems.problems
    assert len(problems) == 1
    assert isinstance(problems[0], validate_actions.Problem)
