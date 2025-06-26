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
        schema = validate_actions.workflow.helper.get_workflow_schema("github-workflow.json")
        contexts = validate_actions.workflow.Contexts()
        events_builder = validate_actions.workflow.BaseEventsBuilder(problems, schema)
        steps_builder = validate_actions.workflow.BaseStepsBuilder(problems, schema, contexts)
        jobs_builder = validate_actions.workflow.BaseJobsBuilder(
            problems, schema, steps_builder, contexts
        )
        job_order_analyzer = validate_actions.workflow.JobOrderAnalyzer()

        director = validate_actions.workflow.BaseDirector(
            temp_file_path,
            yaml_parser,
            problems,
            events_builder,
            jobs_builder,
            contexts,
            job_order_analyzer,
        )
        return director.build()
    finally:
        temp_file_path.unlink(missing_ok=True)
