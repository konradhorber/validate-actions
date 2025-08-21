"""Default implementation of an builder for events."""
from typing import Any, Dict, List, Optional, Tuple, Union, cast

from validate_actions.domain_model import ast
from validate_actions.globals.problems import Problem, ProblemLevel, Problems
from validate_actions.pipeline_stages.builders.interfaces import EventsBuilder


class DefaultEventsBuilder(EventsBuilder):
    """Default implementation of the EventsBuilder interface."""
    def __init__(
        self,
        problems: Problems,
    ) -> None:
        self.problems = problems
        self.RULE_NAME = "events-syntax-error"
        self.ALL_EVENTS = [
            "branch_protection_rule",
            "check_run",
            "check_suite",
            "create",
            "delete",
            "deployment",
            "deployment_status",
            "discussion",
            "discussion_comment",
            "fork",
            "gollum",
            "issue_comment",
            "issues",
            "label",
            "merge_group",
            "milestone",
            "page_build",
            "project",
            "project_card",
            "project_column",
            "public",
            "pull_request",
            "pull_request_review",
            "pull_request_review_comment",
            "pull_request_target",
            "push",
            "registry_package",
            "release",
            "status",
            "watch",
            "workflow_call",
            "workflow_dispatch",
            "workflow_run",
            "repository_dispatch",
        ]

    def build(
        self, events_in: Union[ast.String, Dict[ast.String, Any], List[Any]]
    ) -> List[ast.Event]:
        events: List[ast.Event] = []
        event_out: Optional[ast.Event] = None

        match events_in:
            case ast.String():
                event_out = self.__build_single_event(events_in)
                if event_out is not None:
                    events.append(event_out)

            case dict():
                for event_in, event_in_value in events_in.items():
                    event_out = self.__build_event_from_dict(event_in, event_in_value)
                    if event_out is not None:
                        events.append(event_out)

            case list():
                for event in events_in:
                    if isinstance(event, dict) | isinstance(event, list):
                        self.problems.append(
                            Problem(
                                pos=event.pos,
                                desc="Only flat list of events allowed",
                                level=ProblemLevel.ERR,
                                rule=self.RULE_NAME,
                            )
                        )
                    elif isinstance(event, ast.String):
                        event_out = self.__build_single_event(event)
                        if event_out is not None:
                            events.append(event_out)

            case _:
                self.problems.append(
                    Problem(
                        pos=events_in.pos,
                        desc="Invalid event structure",
                        level=ProblemLevel.ERR,
                        rule=self.RULE_NAME,
                    )
                )

        return events

    def __build_single_event(self, event: ast.String) -> Optional[ast.Event]:
        """Builds events from a single event string.

        Args:
            event (ast.String): the event string.

        Returns:
            Optional[ast.Event]: the event if successful, None otherwise.
        """
        event_out: Optional[ast.Event] = None

        match event.string:
            case "pull_request" | "pull_request_target":
                event_out = ast.PathsBranchesFilterEvent(id=event)
            case "push":
                event_out = ast.TagsPathsBranchesFilterEvent(id=event)
            case "schedule":
                self.problems.append(
                    Problem(
                        pos=event.pos,
                        desc="Schedule event must have a cron expression",
                        level=ProblemLevel.ERR,
                        rule=self.RULE_NAME,
                    )
                )
            case "workflow_call":
                event_out = ast.WorkflowCallEvent(id=event)
            case "workflow_run":
                self.problems.append(
                    Problem(
                        pos=event.pos,
                        desc="workflow_run event must have a workflow set",
                        level=ProblemLevel.ERR,
                        rule=self.RULE_NAME,
                    )
                )
            case "workflow_dispatch":
                event_out = ast.WorkflowDispatchEvent(id=event)
            case s if s in self.ALL_EVENTS:
                event_out = ast.Event(id=event)
            case _:
                self.problems.append(
                    Problem(
                        pos=event.pos,
                        desc=f"Unknown event type: {event.string}",
                        level=ProblemLevel.ERR,
                        rule=self.RULE_NAME,
                    )
                )
        return event_out

    def __build_event_from_dict(
        self, event_in: ast.String, event_in_value: Any
    ) -> Optional[ast.Event]:
        """Builds event from a nested structure with event attributes like
        filters.

        Args:
            event_in (ast.String): the event itself (e.g., pull_request).
            event_in_value (Any): its specific attributes (e.g., filters).

        Returns:
            Optional[ast.Event]: the event if successful, None otherwise.
        """
        event_out: Optional[ast.Event] = None
        match event_in.string:
            case "pull_request" | "pull_request_target":
                event_out = self.__build_PathsBranchesFilterEvent(event_in, event_in_value)
            case "push":
                event_out = self.__build_TagsPathsBranchesFilterEvent(event_in, event_in_value)
            case "schedule":
                event_out = self.__build_ScheduleEvent(event_in, event_in_value)
            case "workflow_call":
                event_out = self.__build_WorkflowCallEvent(event_in, event_in_value)
            case "workflow_run":
                event_out = self.__build_WorkflowRunEvent(event_in, event_in_value)
            case "workflow_dispatch":
                event_out = self.__build_WorkflowDispatchEvent(event_in, event_in_value)
            case s if s in self.ALL_EVENTS:
                event_out = self.__build_Event(event_in, event_in_value)
            case _:
                self.problems.append(
                    Problem(
                        pos=event_in.pos,
                        desc=f"Unknown event type: {event_in.string}",
                        level=ProblemLevel.ERR,
                        rule=self.RULE_NAME,
                    )
                )
        return event_out

    def __build_BranchesFilterEvent(
        self, event_type: ast.String, filters: Dict[ast.String, Any]
    ) -> ast.BranchesFilterEvent:
        """Builds a BranchesFilterEvent from event type and filters.

        Args:
            event_type (ast.String): The event type string(e.g. 'pull_request')
            filters (Dict[ast.String, Any]): Dictionary of filter configs

        Returns:
            ast.BranchesFilterEvent: The constructed event with branch filters
        """
        id = event_type
        types_: Optional[List[ast.String]] = None
        branches_: Optional[List[ast.String]] = None
        branches_ignore_: Optional[List[ast.String]] = None

        for filter, filter_list in filters.items():
            match filter.string:
                case "types":
                    types_ = filter_list
                case "branches":
                    branches_ = filter_list
                case "branches-ignore":
                    branches_ignore_ = filter_list
                case _:
                    self.problems.append(
                        Problem(
                            pos=filter.pos,
                            desc=f"Unknown event filter key: {filter.string}",
                            level=ProblemLevel.ERR,
                            rule=self.RULE_NAME,
                        )
                    )
        return ast.BranchesFilterEvent(
            id=id, types_=types_, branches_=branches_, branches_ignore_=branches_ignore_
        )

    def __build_PathsBranchesFilterEvent(
        self, event_type: ast.String, filters: Dict[ast.String, Any]
    ) -> ast.PathsBranchesFilterEvent:
        """Builds a PathsBranchesFilterEvent with paths and branch filtering.

        Args:
            event_type (ast.String): The event type string
            filters (Dict[ast.String, Any]): Dictionary of filter configs

        Returns:
            ast.PathsBranchesFilterEvent: The constructed event with path and
                branch filters
        """
        # Leverage parent FilterEvent
        parent_filter_options = ["types", "branches", "branches-ignore"]
        parent_filters, addl_filters = self.__split_props(filters, parent_filter_options)

        branches_filter_event = self.__build_BranchesFilterEvent(event_type, parent_filters)

        # Handle paths and paths-ignore
        paths_: Optional[List[ast.String]] = None
        paths_ignore_: Optional[List[ast.String]] = None

        for filter, filter_list in addl_filters.items():
            if filter.string == "paths":
                paths_ = filter_list
            elif filter.string == "paths-ignore":
                paths_ignore_ = filter_list
            else:
                self.problems.append(
                    Problem(
                        pos=filter.pos,
                        desc=f"Unknown event filter key: {filter.string}",
                        level=ProblemLevel.ERR,
                        rule=self.RULE_NAME,
                    )
                )

        return ast.PathsBranchesFilterEvent(
            id=branches_filter_event.id,
            types_=branches_filter_event.types_,
            branches_=branches_filter_event.branches_,
            branches_ignore_=branches_filter_event.branches_ignore_,
            paths_=paths_,
            paths_ignore_=paths_ignore_,
        )

    def __build_TagsPathsBranchesFilterEvent(
        self, event_type: ast.String, filters: Dict[ast.String, Any]
    ) -> ast.TagsPathsBranchesFilterEvent:
        """Builds a TagsPathsBranchesFilterEvent with tags, paths and branch
        filtering.

        Args:
            event_type (ast.String): The event type string
            filters (Dict[ast.String, Any]): Dictionary of filter
                configurations

        Returns:
            ast.TagsPathsBranchesFilterEvent: The constructed event with all
                filters
        """
        # Leverage parent FilterEvent
        parent_filter_options = ["types", "branches", "branches-ignore", "paths", "paths-ignore"]
        parent_filters, addl_filters = self.__split_props(filters, parent_filter_options)

        paths_branches_filter_event = self.__build_PathsBranchesFilterEvent(
            event_type, parent_filters
        )

        # Handle tags and tags-ignore
        tags_: Optional[List[ast.String]] = None
        tags_ignore_: Optional[List[ast.String]] = None

        for filter, filter_list in addl_filters.items():
            if filter.string == "tags":
                tags_ = filter_list
            elif filter.string == "tags-ignore":
                tags_ignore_ = filter_list
            else:
                self.problems.append(
                    Problem(
                        pos=filter.pos,
                        desc=f"Unknown event filter key: {filter.string}",
                        level=ProblemLevel.ERR,
                        rule=self.RULE_NAME,
                    )
                )

        return ast.TagsPathsBranchesFilterEvent(
            id=paths_branches_filter_event.id,
            types_=paths_branches_filter_event.types_,
            branches_=paths_branches_filter_event.branches_,
            branches_ignore_=paths_branches_filter_event.branches_ignore_,
            paths_=paths_branches_filter_event.paths_,
            paths_ignore_=paths_branches_filter_event.paths_ignore_,
            tags_=tags_,
            tags_ignore_=tags_ignore_,
        )

    def __build_ScheduleEvent(
        self, event_type: ast.String, crons: List[dict]
    ) -> ast.ScheduleEvent:
        """Builds a ScheduleEvent from cron expressions.

        Args:
            event_type (ast.String): The schedule event identifier
            crons (List[dict]): List of cron expression dictionaries

        Returns:
            ast.ScheduleEvent: The constructed schedule event with cron
                expressions
        """
        if not isinstance(crons, list):
            pass

        cron_list: List[ast.String] = []
        for cron in crons:
            cron_k = next(iter(cron))
            cron_v = cron[cron_k]
            if (
                not isinstance(cron, dict)
                or len(cron) != 1
                or cron_k.string != "cron"
                or not isinstance(cron_v, ast.String)
            ):
                self.problems.append(
                    Problem(
                        pos=event_type.pos,
                        desc="Schedule event must have a valid cron expression",
                        level=ProblemLevel.ERR,
                        rule=self.RULE_NAME,
                    )
                )
            else:
                cron_list.append(cron_v)

        event_out = ast.ScheduleEvent(id=event_type, cron_=cron_list)
        return event_out

    def __build_WorkflowCallEvent(
        self, event_name: ast.String, event_value: Dict[ast.String, Any]
    ):
        """Builds a WorkflowCallEvent from event properties.

        Args:
            event_name (ast.String): The workflow_call event identifier
            event_value (Dict[ast.String, Any]): Dictionary of event properties

        Returns:
            ast.WorkflowCallEvent: The constructed workflow_call event
        """
        types_: Optional[List[ast.String]] = None
        inputs_: Optional[List[ast.WorkflowCallEventInput]] = None
        outputs_: Optional[List[ast.WorkflowCallEventOutput]] = None
        secrets_: Optional[List[ast.WorkflowCallEventSecret]] = None

        for key, value in event_value.items():
            match key.string:
                case "types":
                    types_ = value
                case "inputs":
                    inputs_ = self.__build_WorkflowCallEventInputs(value)
                case "outputs":
                    outputs_ = self.__build_WorkflowCallEventOutputs(value)
                case "secrets":
                    secrets_ = self.__buildWorkflowCallEventSecrets(value)
                case _:
                    self.problems.append(
                        Problem(
                            pos=key.pos,
                            desc=("Unknown workflow_call event attribute " f"{key.string}"),
                            level=ProblemLevel.ERR,
                            rule=self.RULE_NAME,
                        )
                    )

        return ast.WorkflowCallEvent(
            id=event_name,
            types_=types_,
            inputs_=inputs_,
            outputs_=outputs_,
            secrets_=secrets_,
        )

    def __build_WorkflowCallEventInputs(
        self, inputs_in: Dict[ast.String, Dict[ast.String, Union[ast.String, bool]]]
    ) -> Optional[List[ast.WorkflowCallEventInput]]:
        """Builds WorkflowCallEventInput objects from input definitions.

        Args:
            inputs_in
                (Dict[ast.String, Dict[ast.String, Union[ast.String, bool]]]):
                Dictionary of input definitions

        Returns:
            Optional[List[ast.WorkflowCallEventInput]]: List of input objects
            or None
        """
        inputs_out: List[ast.WorkflowCallEventInput] = []

        for input_name, input_props in inputs_in.items():
            input = self.__build_WorkflowCallEventInput(input_name, input_props)
            # ignores faulty input
            if input is not None:
                inputs_out.append(input)
        # returns None if all inputs are faulty
        if len(inputs_out) == 0:
            None
        return inputs_out

    def __build_WorkflowEventInput(
        self, input_props: Dict[ast.String, Union[ast.String, bool]]
    ) -> Dict[str, Optional[Union[ast.String, bool]]]:
        """Extracts basic input properties shared across workflow event inputs.

        Args:
            input_props (Dict[ast.String, Union[ast.String, bool]]):
                Dictionary of input properties

        Returns:
            Dict[str, Optional[Union[ast.String, bool]]]: Extracted base
                properties
        """
        description_: Optional[ast.String] = None
        default_: Optional[ast.String] = None
        required_: bool = False

        types = {
            "description": (ast.String, "workflow event input 'description' must be a string"),
            "default": (ast.String, "workflow event input 'property' default must be a string"),
            "required": (bool, "workflow event input 'required' must be a boolean"),
        }

        for key, value in input_props.items():
            key_name = key.string

            if key_name in types:
                expected_type, error_msg = types[key_name]

                if isinstance(value, expected_type):
                    if key_name == "description":
                        description_ = cast(ast.String, value)
                    elif key_name == "default":
                        default_ = cast(ast.String, value)
                    elif key_name == "required":
                        required_ = cast(bool, value)
                else:
                    self.problems.append(
                        Problem(
                            pos=key.pos,
                            desc=error_msg,
                            level=ProblemLevel.ERR,
                            rule=self.RULE_NAME,
                        )
                    )
        return {
            "description": description_,
            "default": default_,
            "required": required_,
        }

    def __build_WorkflowCallEventInput(
        self, input_name: ast.String, input_props: Dict[ast.String, Union[ast.String, bool]]
    ) -> Optional[ast.WorkflowCallEventInput]:
        """Builds a WorkflowCallEventInput from input name and properties.

        Args:
            input_name (ast.String): The input identifier
            input_props (Dict[ast.String, Union[ast.String, bool]]): Input
                properties

        Returns:
            Optional[ast.WorkflowCallEventInput]: The constructed input or
                None if invalid
        """
        base_input_prop_options = ["description", "default", "required"]
        base_input_props, call_input_props = self.__split_props(
            input_props, base_input_prop_options
        )

        input_base_values = self.__build_WorkflowEventInput(base_input_props)

        type_: Optional[ast.WorkflowCallInputType] = None

        types = {"type": (ast.String, "Incorrect workflow_call input type")}

        for key, value in call_input_props.items():
            key_name = key.string

            if key_name in types:
                expected_type, error_msg = types[key_name]

                if isinstance(value, expected_type):
                    if key_name == "type":
                        s = cast(ast.String, value).string
                        if s in ast.WorkflowCallInputType.__members__:
                            type_ = ast.WorkflowCallInputType[s]
                        else:
                            self.problems.append(
                                Problem(
                                    pos=key.pos,
                                    desc=error_msg,
                                    level=ProblemLevel.ERR,
                                    rule=self.RULE_NAME,
                                )
                            )
                else:
                    self.problems.append(
                        Problem(
                            pos=key.pos,
                            desc=error_msg,
                            level=ProblemLevel.ERR,
                            rule=self.RULE_NAME,
                        )
                    )
            else:
                self.problems.append(
                    Problem(
                        pos=key.pos,
                        desc=f"Unknown workflow_call property: {key_name}",
                        level=ProblemLevel.ERR,
                        rule=self.RULE_NAME,
                    )
                )

        if type_ is None:
            self.problems.append(
                Problem(
                    pos=input_name.pos,
                    desc="workflow_call event input type is required",
                    level=ProblemLevel.ERR,
                    rule=self.RULE_NAME,
                )
            )
            return None

        return ast.WorkflowCallEventInput(
            id=input_name,
            description_=cast(Optional[ast.String], input_base_values["description"]),
            default_=cast(Optional[ast.String], input_base_values["default"]),
            required_=cast(bool, input_base_values["required"]),
            type_=type_,
        )

    def __build_WorkflowCallEventOutputs(
        self, outputs_in: Dict[ast.String, Dict[ast.String, ast.String]]
    ) -> Optional[List[ast.WorkflowCallEventOutput]]:
        """Builds WorkflowCallEventOutput objects from output definitions.

        Args:
            outputs_in (Dict[ast.String, Dict[ast.String, ast.String]]):
                Dictionary of output definitions

        Returns:
            Optional[List[ast.WorkflowCallEventOutput]]: List of output
                objects or None
        """
        outputs_out: List[ast.WorkflowCallEventOutput] = []

        for output_name, output_props in outputs_in.items():
            output = self.__build_WorkflowCallEventOutput(output_name, output_props)
            # ignores faulty output
            if output is not None:
                outputs_out.append(output)
        # returns None if all outputs are faulty
        if len(outputs_out) == 0:
            return None
        return outputs_out

    def __build_WorkflowCallEventOutput(
        self, output_name: ast.String, output_props: Dict[ast.String, ast.String]
    ) -> Optional[ast.WorkflowCallEventOutput]:
        """Builds a WorkflowCallEventOutput from output name and properties.

        Args:
            output_name (ast.String): The output identifier
            output_props (Dict[ast.String, ast.String]): Output properties

        Returns:
            Optional[ast.WorkflowCallEventOutput]: The constructed output or
                None
        """
        id = output_name
        value_: ast.String
        description_: Optional[ast.String] = None

        for key, value in output_props.items():
            match key.string:
                case "value":
                    value_ = value
                case "description":
                    description_ = value
                case _:
                    self.problems.append(
                        Problem(
                            pos=key.pos,
                            desc=(
                                "Unknown workflow_call event output attribute: " f"{key.string}"
                            ),
                            level=ProblemLevel.ERR,
                            rule=self.RULE_NAME,
                        )
                    )

        if not isinstance(value_, ast.String):
            self.problems.append(
                Problem(
                    pos=output_name.pos,
                    desc="workflow_call event output value is required",
                    level=ProblemLevel.ERR,
                    rule=self.RULE_NAME,
                )
            )
            return None

        return ast.WorkflowCallEventOutput(id=id, value_=value_, description_=description_)

    def __buildWorkflowCallEventSecrets(
        self,
        secrets_in: Dict[ast.String, Union[ast.String, Dict[ast.String, Union[ast.String, bool]]]],
    ) -> List[ast.WorkflowCallEventSecret]:
        """Builds WorkflowCallEventSecret objects from secret definitions.

        Args:
            secrets_in (Dict): Dictionary of secret definitions with varying
                formats

        Returns:
            List[ast.WorkflowCallEventSecret]: List of constructed secret
                objects
        """
        secrets_out: List[ast.WorkflowCallEventSecret] = []
        error_desc = "workflow_call event secret syntax error"

        for secret_id, secret_value in secrets_in.items():
            secret: ast.WorkflowCallEventSecret
            if isinstance(secret_value, ast.String):
                secret = ast.WorkflowCallEventSecret(
                    id=secret_id,
                )
            elif isinstance(secret_value, dict):
                description_: Optional[ast.String] = None
                required_: bool = False
                for key, value in secret_value.items():
                    if key.string == "description" and isinstance(value, ast.String):
                        description_ = value
                    elif key.string == "required" and isinstance(value, bool):
                        required_ = value
                    else:
                        self.problems.append(
                            Problem(
                                pos=key.pos,
                                desc=error_desc,
                                level=ProblemLevel.ERR,
                                rule=self.RULE_NAME,
                            )
                        )
                secret = ast.WorkflowCallEventSecret(
                    id=secret_id, description_=description_, required_=required_
                )
            else:
                self.problems.append(
                    Problem(
                        pos=secret_id.pos,
                        desc=error_desc,
                        level=ProblemLevel.ERR,
                        rule=self.RULE_NAME,
                    )
                )
                continue
            secrets_out.append(secret)
        return secrets_out

    def __build_WorkflowRunEvent(
        self, event_type: ast.String, event_value: Dict[ast.String, Any]
    ) -> Optional[ast.WorkflowRunEvent]:
        """Builds a WorkflowRunEvent with workflows and branch filtering.

        Args:
            event_type (ast.String): The workflow_run event identifier
            event_value (Dict[ast.String, Any]): Dictionary of event properties

        Returns:
            Optional[ast.WorkflowRunEvent]: The constructed event or None if
                invalid
        """
        # Leverage parent FilterEvent
        parent_filter_options = ["types", "branches", "branches-ignore"]
        parent_filters, addl_value = self.__split_props(event_value, parent_filter_options)
        branches_filter_event = self.__build_BranchesFilterEvent(event_type, parent_filters)

        # Handle workflows
        workflows_: List[ast.String] = []
        # Value not handled by parent filters
        addl_value = {
            key: value
            for key, value in event_value.items()
            if key.string not in parent_filter_options
        }

        for key, value in addl_value.items():
            if key.string == "workflows":
                workflows_ = value
            else:
                self.problems.append(
                    Problem(
                        pos=key.pos,
                        desc=f"Unknown event filter key: {key.string}",
                        level=ProblemLevel.ERR,
                        rule=self.RULE_NAME,
                    )
                )

        if len(workflows_) == 0:
            self.problems.append(
                Problem(
                    pos=event_type.pos,
                    desc="workflow_run event requires workflow specification",
                    level=ProblemLevel.ERR,
                    rule=self.RULE_NAME,
                )
            )
            return None

        return ast.WorkflowRunEvent(
            id=branches_filter_event.id,
            types_=branches_filter_event.types_,
            branches_=branches_filter_event.branches_,
            branches_ignore_=branches_filter_event.branches_ignore_,
            workflows_=workflows_,
        )

    def __build_WorkflowDispatchEvent(
        self, event_type: ast.String, event_value: Dict[ast.String, Any]
    ) -> ast.WorkflowDispatchEvent:
        """Builds a WorkflowDispatchEvent from manual trigger configuration.

        Args:
            event_type (ast.String): The workflow_dispatch event identifier
            event_value (Dict[ast.String, Any]): Dictionary of event properties

        Returns:
            ast.WorkflowDispatchEvent: The constructed workflow_dispatch event
        """
        inputs_: Optional[List[ast.WorkflowDispatchEventInput]] = None

        for key, value in event_value.items():
            if key.string == "inputs":
                inputs_ = self.__build_WorkflowDispatchEventInputs(value)
            else:
                self.problems.append(
                    Problem(
                        pos=key.pos,
                        desc=f"Unknown workflow_dispatch attribute: {key.string}",
                        level=ProblemLevel.ERR,
                        rule=self.RULE_NAME,
                    )
                )

        return ast.WorkflowDispatchEvent(id=event_type, inputs_=inputs_)

    def __build_WorkflowDispatchEventInputs(
        self, inputs_in: Dict[ast.String, Dict[ast.String, Union[ast.String, bool]]]
    ) -> Optional[List[ast.WorkflowDispatchEventInput]]:
        """Builds WorkflowDispatchEventInput objects from input definitions.

        Args:
            inputs_in
                (Dict[ast.String, Dict[ast.String, Union[ast.String, bool]]]):
                Dictionary of input definitions

        Returns:
            Optional[List[ast.WorkflowDispatchEventInput]]: List of input
                objects or None
        """
        inputs_out: List[ast.WorkflowDispatchEventInput] = []

        for input_name, input_props in inputs_in.items():
            input = self.__build_WorkflowDispatchEventInput(input_name, input_props)
            # ignores faulty input
            if input is not None:
                inputs_out.append(input)
        # returns None if all inputs are faulty
        if len(inputs_out) == 0:
            return None
        return inputs_out

    def __build_WorkflowDispatchEventInput(
        self, input_name: ast.String, input_props: Dict[ast.String, Union[ast.String, bool]]
    ) -> Optional[ast.WorkflowDispatchEventInput]:
        """Builds a WorkflowDispatchEventInput from input name and properties.

        Args:
            input_name (ast.String): The input identifier
            input_props (Dict[ast.String, Union[ast.String, bool]]): Input
                properties

        Returns:
            Optional[ast.WorkflowDispatchEventInput]: The constructed input or
                None
        """
        base_input_prop_options = ["description", "default", "required"]
        base_input_props, dispatch_input_props = self.__split_props(
            input_props, base_input_prop_options
        )

        input_base_values = self.__build_WorkflowEventInput(base_input_props)

        type_: Optional[ast.WorkflowDispatchInputType] = None
        options_: Optional[List[ast.String]] = None

        types = {
            "type": (ast.String, "Incorrect workflow_dispatch input type"),
            "options": (list, "workflow_dispatch event input options must be a list"),
        }

        for key, value in dispatch_input_props.items():
            key_name = key.string

            if key_name in types:
                expected_type, error_msg = types[key_name]

                if isinstance(value, expected_type):
                    if key_name == "type":
                        s = cast(ast.String, value).string
                        if s in ast.WorkflowDispatchInputType.__members__:
                            type_ = ast.WorkflowDispatchInputType[s]
                        else:
                            self.problems.append(
                                Problem(
                                    pos=key.pos,
                                    desc=error_msg,
                                    level=ProblemLevel.ERR,
                                    rule=self.RULE_NAME,
                                )
                            )
                    elif key_name == "options":
                        options_ = cast(list, value)
                else:
                    self.problems.append(
                        Problem(
                            pos=key.pos,
                            desc=error_msg,
                            level=ProblemLevel.ERR,
                            rule=self.RULE_NAME,
                        )
                    )
            else:
                self.problems.append(
                    Problem(
                        pos=key.pos,
                        desc=f"Unknown workflow_dispatch property: {key_name}",
                        level=ProblemLevel.ERR,
                        rule=self.RULE_NAME,
                    )
                )

        if type_ is None:
            self.problems.append(
                Problem(
                    pos=input_name.pos,
                    desc="workflow_dispatch event input type is required",
                    level=ProblemLevel.ERR,
                    rule=self.RULE_NAME,
                )
            )
            return None

        # validate options
        choice_type = ast.WorkflowDispatchInputType.choice.name
        if type_.name == choice_type and options_ is None:
            self.problems.append(
                Problem(
                    pos=input_name.pos,
                    desc="workflow_dispatch event input options is required",
                    level=ProblemLevel.ERR,
                    rule=self.RULE_NAME,
                )
            )
            return None
        if options_ is not None and type_.name != choice_type:
            self.problems.append(
                Problem(
                    pos=input_name.pos,
                    desc=(
                        "workflow_dispatch event input options is only " "valid for type choice"
                    ),
                    level=ProblemLevel.ERR,
                    rule=self.RULE_NAME,
                )
            )
            return None

        return ast.WorkflowDispatchEventInput(
            id=input_name,
            description_=cast(Optional[ast.String], input_base_values["description"]),
            default_=cast(Optional[ast.String], input_base_values["default"]),
            required_=cast(bool, input_base_values["required"]),
            type_=type_,
            options_=options_,
        )

    def __build_Event(
        self, event_type: ast.String, event_value: Dict[ast.String, Any]
    ) -> ast.Event:
        """Builds a basic Event object with optional types filter.

        Args:
            event_type (ast.String): The event identifier
            event_value (Dict[ast.String, Any]): Dictionary of event properties

        Returns:
            ast.Event: The constructed basic event
        """
        id = event_type
        types_: Optional[List[ast.String]] = None

        for key, value in event_value.items():
            if key.string == "types":
                types_ = value
            else:
                self.problems.append(
                    Problem(
                        pos=key.pos,
                        desc=f"Unknown event filter key: {key.string}",
                        level=ProblemLevel.ERR,
                        rule=self.RULE_NAME,
                    )
                )

        return ast.Event(id=id, types_=types_)

    def __split_props(
        self, props: Dict[ast.String, Any], parent_prop_options: List[str]
    ) -> Tuple[Dict[ast.String, Any], Dict[ast.String, Any]]:
        """
        Split properties (e.g., event filters) into already handled by parent
        and to be handled by child (current level).

        Args:
            props: The event configuration dictionary
            parent_prop_options: List of properties that would belong to parent

        Returns:
            Tuple of (parent_props, child_props)
        """
        # Extract parent filters
        parent_props = {
            key: value for key, value in props.items() if key.string in parent_prop_options
        }

        # Extract child/remaining filters
        child_props = {
            key: value for key, value in props.items() if key.string not in parent_prop_options
        }

        return parent_props, child_props
