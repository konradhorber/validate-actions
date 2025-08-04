import tempfile
from pathlib import Path
from typing import Tuple

import validate_actions


def parse_workflow_string(
    workflow_string: str,
) -> Tuple[validate_actions.workflow.Workflow, validate_actions.Problems]:
    """
    Helper function to parse a workflow string into a Workflow object.

    Args:
        workflow_string (str): The workflow YAML content as a string

    Returns:
        Tuple[Workflow, List[LintProblem]]: The parsed workflow and any
        problems found
    """
    with tempfile.NamedTemporaryFile(suffix=".yml", mode="w+", delete=False) as temp_file:
        temp_file.write(workflow_string)
        temp_file_path = Path(temp_file.name)

    try:
        yaml_parser = validate_actions.workflow.PyYAMLParser()
        problems = validate_actions.Problems()
        contexts = validate_actions.workflow.Contexts()
        events_builder = validate_actions.workflow.EventsBuilder(problems)
        steps_builder = validate_actions.workflow.StepsBuilder(problems, contexts)
        jobs_builder = validate_actions.workflow.JobsBuilder(
            problems, steps_builder, contexts
        )
        job_orderer = validate_actions.job_orderer.JobOrderer(problems)

        # Parse the workflow file first
        workflow_dict, parser_problems = yaml_parser.parse(temp_file_path)
        problems.extend(parser_problems)
        
        # Build workflow from parsed dict
        director = validate_actions.workflow.WorkflowBuilder(
            workflow_dict,
            problems,
            events_builder,
            jobs_builder,
            contexts,
        )
        workflow, problems = director.build()
        
        # Prepare workflow with job dependency analysis and needs contexts
        job_orderer.prepare_workflow(workflow)
        
        return workflow, problems
    finally:
        temp_file_path.unlink(missing_ok=True)
