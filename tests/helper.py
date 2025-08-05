import tempfile
from pathlib import Path
from typing import Tuple

import validate_actions
from validate_actions.building import (
    events_builder,
    jobs_builder,
    shared_components_builder,
    steps_builder,
    workflow_builder,
)
from validate_actions.core import problems
from validate_actions.domain_model import contexts
from validate_actions.ordering import job_orderer
from validate_actions.parsing import parser


def parse_workflow_string(
    workflow_string: str,
) -> Tuple[validate_actions.domain_model.ast.Workflow, problems.Problems]:
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
        yaml_parser = parser.PyYAMLParser()
        problems_instance = problems.Problems()
        contexts_instance = contexts.Contexts()
        shared_components_builder_instance = shared_components_builder.SharedComponentsBuilder(problems_instance)
        events_builder_instance = events_builder.EventsBuilder(problems_instance)
        steps_builder_instance = steps_builder.StepsBuilder(problems_instance, contexts_instance, shared_components_builder_instance)
        jobs_builder_instance = jobs_builder.JobsBuilder(
            problems_instance, steps_builder_instance, contexts_instance, shared_components_builder_instance
        )
        job_orderer_instance = job_orderer.JobOrderer(problems_instance)

        # Parse the workflow file first
        workflow_dict, parser_problems = yaml_parser.parse(temp_file_path)
        problems_instance.extend(parser_problems)
        
        # Build workflow from parsed dict
        director = workflow_builder.WorkflowBuilder(
            workflow_dict,
            problems_instance,
            events_builder_instance,
            jobs_builder_instance,
            contexts_instance,
            shared_components_builder_instance,
        )
        workflow, workflow_problems = director.build()
        
        # Prepare workflow with job dependency analysis and needs contexts
        job_orderer_instance.prepare_workflow(workflow)
        
        return workflow, problems_instance
    finally:
        temp_file_path.unlink(missing_ok=True)
