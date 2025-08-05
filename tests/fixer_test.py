"""Tests for the fixer batch/flush behavior with multiple edits."""

import tempfile
from pathlib import Path

from validate_actions.core.problems import Problem, ProblemLevel
from validate_actions.domain_model.pos import Pos
from validate_actions.fixing.fixer import BaseFixer


class TestFixerBatchEdits:
    """Test cases for fixer batch edit collection and flush behavior."""

    def test_edits_are_deferred_until_flush(self):
        """
        Test that edit_yaml_at_position() collects edits without applying them
        immediately, and flush() applies all edits at once.
        """
        workflow_content = """name: test
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout
      - uses: actions/setup-node@v3
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write(workflow_content)
            temp_path = Path(f.name)

        try:
            fixer = BaseFixer(temp_path)
            
            problem1 = Problem(
                Pos(6, 15, 73), ProblemLevel.WAR, "Missing version", "test-rule"
            )
            problem2 = Problem(
                Pos(7, 15, 107), ProblemLevel.WAR, "Outdated version", "test-rule"
            )
            
            # Add edits but don't flush yet
            fixer.edit_yaml_at_position(
                73, "actions/checkout", "actions/checkout@v4", problem1, "Added version"
            )
            fixer.edit_yaml_at_position(
                107, "actions/setup-node@v3", "actions/setup-node@v4", problem2, "Updated version"
            )
            
            # File should be unchanged until flush()
            with open(temp_path, 'r') as f:
                content_before_flush = f.read()
            
            assert content_before_flush == workflow_content, "File should not change until flush()"
            
            # Now flush the edits
            fixer.flush()
            
            # File should now be updated
            with open(temp_path, 'r') as f:
                content_after_flush = f.read()
            
            assert "actions/checkout@v4" in content_after_flush
            assert "actions/setup-node@v4" in content_after_flush
            assert content_after_flush != workflow_content
            
        finally:
            temp_path.unlink(missing_ok=True)

    def test_flush_applies_edits_in_descending_position_order(self):
        """
        Test that flush() sorts edits by position in descending order
        (end-of-file to beginning) to avoid position corruption.
        """
        workflow_content = """name: test
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout
      - uses: actions/setup-node@v3
      - uses: actions/upload-artifact
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write(workflow_content)
            temp_path = Path(f.name)

        try:
            fixer = BaseFixer(temp_path)
            
            # Add edits in random order (not file position order)
            problem2 = Problem(Pos(7, 15, 107), ProblemLevel.WAR, "Outdated", "test-rule")
            problem1 = Problem(Pos(6, 15, 73), ProblemLevel.WAR, "Missing", "test-rule")
            problem3 = Problem(Pos(8, 15, 141), ProblemLevel.WAR, "Missing", "test-rule")
            
            # Add edits in middle, first, last order
            fixer.edit_yaml_at_position(107, "actions/setup-node@v3", "actions/setup-node@v4", problem2, "Updated")
            fixer.edit_yaml_at_position(73, "actions/checkout", "actions/checkout@v4", problem1, "Added")
            fixer.edit_yaml_at_position(141, "actions/upload-artifact", "actions/upload-artifact@v3", problem3, "Added")
            
            # Verify edits are stored in the order they were added
            assert len(fixer.pending_edits) == 3
            assert fixer.pending_edits[0]['idx'] == 107  # Middle
            assert fixer.pending_edits[1]['idx'] == 73   # First
            assert fixer.pending_edits[2]['idx'] == 141  # Last
            
            fixer.flush()
            
            # File should have all edits applied correctly
            with open(temp_path, 'r') as f:
                final_content = f.read()
            
            assert "actions/checkout@v4" in final_content
            assert "actions/setup-node@v4" in final_content
            assert "actions/upload-artifact@v3" in final_content
            
        finally:
            temp_path.unlink(missing_ok=True)

    def test_out_of_order_fixes_work_correctly_with_batching(self):
        """
        Test that the batching approach fixes the out-of-order indexing issue
        that was demonstrated in the original corruption test.
        """
        workflow_content = """name: test
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout
      - uses: actions/setup-node@v3
      - uses: actions/upload-artifact
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write(workflow_content)
            temp_path = Path(f.name)

        try:
            fixer = BaseFixer(temp_path)
            
            problem1 = Problem(Pos(6, 15, 73), ProblemLevel.WAR, "Missing", "test-rule")
            problem2 = Problem(Pos(7, 15, 107), ProblemLevel.WAR, "Outdated", "test-rule")
            problem3 = Problem(Pos(8, 15, 141), ProblemLevel.WAR, "Missing", "test-rule")
            
            # Apply fixes in the WORST possible order (reverse file order)
            # This would have caused corruption in the old implementation
            fixer.edit_yaml_at_position(141, "actions/upload-artifact", "actions/upload-artifact@v3", problem3, "Added")
            fixer.edit_yaml_at_position(107, "actions/setup-node@v3", "actions/setup-node@v4", problem2, "Updated")
            fixer.edit_yaml_at_position(73, "actions/checkout", "actions/checkout@v4", problem1, "Added")
            
            fixer.flush()
            
            # Read final content
            with open(temp_path, 'r') as f:
                final_content = f.read()
            
            # All fixes should be applied correctly despite out-of-order application
            assert "actions/checkout@v4" in final_content
            assert "actions/setup-node@v4" in final_content
            assert "actions/upload-artifact@v3" in final_content
            
            # Verify the structure is intact (no corruption)
            lines = final_content.splitlines()
            checkout_line = next((line for line in lines if "checkout" in line), None)
            setup_line = next((line for line in lines if "setup-node" in line), None)
            upload_line = next((line for line in lines if "upload-artifact" in line), None)
            
            assert checkout_line and "actions/checkout@v4" in checkout_line
            assert setup_line and "actions/setup-node@v4" in setup_line
            assert upload_line and "actions/upload-artifact@v3" in upload_line
            
        finally:
            temp_path.unlink(missing_ok=True)

    def test_multiple_flush_calls_are_safe(self):
        """
        Test that calling flush() multiple times doesn't cause issues.
        """
        workflow_content = """name: test
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write(workflow_content)
            temp_path = Path(f.name)

        try:
            fixer = BaseFixer(temp_path)
            
            problem = Problem(Pos(6, 15, 73), ProblemLevel.WAR, "Missing", "test-rule")
            fixer.edit_yaml_at_position(73, "actions/checkout", "actions/checkout@v4", problem, "Added")
            
            # First flush should apply the edit
            fixer.flush()
            
            with open(temp_path, 'r') as f:
                content_after_first_flush = f.read()
            
            assert "actions/checkout@v4" in content_after_first_flush
            
            # Second flush should be a no-op
            fixer.flush()
            
            with open(temp_path, 'r') as f:
                content_after_second_flush = f.read()
            
            assert content_after_first_flush == content_after_second_flush
            
        finally:
            temp_path.unlink(missing_ok=True)