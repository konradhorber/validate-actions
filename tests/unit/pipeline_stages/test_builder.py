"""Unit tests for AST building coordination."""

from unittest.mock import Mock, patch

from validate_actions.domain_model.ast import Workflow
from validate_actions.domain_model.primitives import Pos, String
from validate_actions.globals.problems import Problems
from validate_actions.pipeline_stages.builder import Builder, DefaultBuilder


class TestBuilder:
    """Unit tests for Builder AST coordination."""

    def test_builder_implements_interface(self):
        """Test that Builder properly implements IBuilder interface."""
        problems = Problems()
        builder = DefaultBuilder(problems)

        assert isinstance(builder, Builder)
        assert hasattr(builder, "process")

    def test_builder_initialization_creates_sub_builders(self):
        """Test that Builder properly initializes all sub-builder components."""
        problems = Problems()
        builder = DefaultBuilder(problems)

        assert hasattr(builder, "shared_components_builder")
        assert hasattr(builder, "events_builder")
        assert hasattr(builder, "steps_builder")
        assert hasattr(builder, "jobs_builder")
        assert hasattr(builder, "workflow_builder")
        assert builder.problems is problems

    @patch("validate_actions.pipeline_stages.builder.DefaultWorkflowBuilder")
    def test_process_delegates_to_workflow_builder(self, mock_workflow_builder_class):
        """Test that process method delegates to workflow builder."""
        problems = Problems()
        mock_workflow_builder = Mock()
        mock_workflow_builder_class.return_value = mock_workflow_builder

        expected_workflow = Mock(spec=Workflow)
        mock_workflow_builder.process.return_value = expected_workflow

        builder = DefaultBuilder(problems)
        workflow_dict = {String("name", Pos(1, 1, 0)): String("test-workflow", Pos(1, 7, 6))}

        result = builder.process(workflow_dict)

        mock_workflow_builder.process.assert_called_once_with(workflow_dict)
        assert result is expected_workflow

    def test_builder_passes_problems_to_all_components(self):
        """Test that Problems instance is passed to all builder components."""
        problems = Problems()

        with patch.multiple(
            "validate_actions.pipeline_stages.builder",
            DefaultSharedComponentsBuilder=Mock(),
            DefaultEventsBuilder=Mock(),
            DefaultStepsBuilder=Mock(),
            DefaultJobsBuilder=Mock(),
            DefaultWorkflowBuilder=Mock(),
        ) as mocks:
            # Verify all builders were instantiated with problems
            for mock_class in mocks.values():
                mock_class.assert_called_once()
                # Check that problems was passed as first argument
                args = mock_class.call_args[0] if mock_class.call_args[0] else []
                kwargs = mock_class.call_args[1] if mock_class.call_args[1] else {}
                assert problems in args or problems in kwargs.values()
