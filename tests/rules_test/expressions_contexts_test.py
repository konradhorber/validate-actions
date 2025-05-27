# flake8: noqa: E501

from tests.helper import parse_workflow_string
from validate_actions import rules
from validate_actions.problems import Problem, ProblemLevel


def test_job_outputs_input_match():
    workflow_matches_string = """
    name: Reusable workflow

    on:
      workflow_call:

        # Map the workflow outputs to job outputs
        outputs:
          firstword:
            description: "The first output string"
            value: ${{ jobs.example_job.outputs.output1 }}
          secondword:
            description: "The second output string"
            value: ${{ jobs.example_job.outputs.output2 }}

    jobs:
      example_job:
        name: Generate output
        runs-on: ubuntu-latest
        
        # Map the job outputs to step outputs
        outputs:
          output1: ${{ steps.step1.outputs.firstword }}
          output2: ${{ steps.step2.outputs.secondword }}
        
        steps:
        - id: step1
          run: echo "firstword=hello" >> $GITHUB_OUTPUT
        - id: step2
          run: echo "secondword=world" >> $GITHUB_OUTPUT
    """
    workflow_matches, problems_matches = parse_workflow_string(workflow_matches_string)
    gen_matches = rules.ExpressionsContexts.check(workflow_matches)
    result_matches = list(gen_matches)
    assert result_matches == []
    
    workflow_doesnt_match_string = """
    name: Reusable workflow

    on:
      workflow_call:

        # Map the workflow outputs to job outputs
        outputs:
          firstword:
            description: "The first output string"
            value: ${{ jobs.example_job.outputs.out1 }}
          secondword:
            description: "The second output string"
            value: ${{ jobs.example_job.outputs.output2 }}

    jobs:
      example_job:
        name: Generate output
        runs-on: ubuntu-latest
        
        # Map the job outputs to step outputs
        outputs:
          output1: ${{ steps.step1.outputs.firstword }}
          output2: ${{ steps.step2.outputs.secondword }}
        
        steps:
        - id: step1
          run: echo "firstword=hello" >> $GITHUB_OUTPUT
        - id: step2
          run: echo "secondword=world" >> $GITHUB_OUTPUT
    """
    workflow_doesnt_match, problems_doesnt_match = parse_workflow_string(workflow_doesnt_match_string)
    gen_doesnt_match = rules.ExpressionsContexts.check(workflow_doesnt_match)
    result_doesnt_match = list(gen_doesnt_match)
    assert len(result_doesnt_match) == 1
    assert result_doesnt_match[0].rule == 'expressions-contexts'

def test_env_match():
    workflow_string = """
    name: 'Test Steps IO Match with uses'

    on: workflow_dispatch
    
    env:
      my_var: 'some_value'

    jobs:
      test-job:
        runs-on: ubuntu-latest
        steps:

        - id: step2
          name: 'Upload artifact'
          uses: actions/upload-artifact@v3
          with:
            name: my-artifact
            path: ${{ env.my_var }}  # Reference to output from env var
    """
    workflow, problems = parse_workflow_string(workflow_string)
    gen = rules.StepsIOMatch.check(workflow)
    result = list(gen)
    assert result == []
    
    workflow_string = """
    name: 'Test Steps IO Match with uses'

    on: workflow_dispatch
    
    env:
      my_var: 'some_value'

    jobs:
      test-job:
        runs-on: ubuntu-latest
        steps:

        - id: step2
          name: 'Upload artifact'
          uses: actions/upload-artifact@v3
          with:
            name: my-artifact
            path: ${{ env.myvar }}  # Reference to output from non-existent env var
    """
    workflow, problems = parse_workflow_string(workflow_string)
    gen = rules.ExpressionsContexts.check(workflow)
    result = list(gen)
    assert len(result) == 1
