"""Unit tests for CLI configuration."""

from validate_actions.globals.cli_config import CLIConfig


class TestCLIConfig:
    """Unit tests for the CLIConfig dataclass."""

    def test_config_creation_minimal(self):
        """Test creating config with only required parameters."""
        config = CLIConfig(fix=False)
        
        assert config.fix is False
        assert config.workflow_file is None
        assert config.github_token is None
        assert config.no_warnings is False

    def test_config_creation_all_parameters(self):
        """Test creating config with all parameters specified."""
        config = CLIConfig(
            fix=True,
            workflow_file="/path/to/workflow.yml",
            github_token="ghp_token123",
            no_warnings=True
        )
        
        assert config.fix is True
        assert config.workflow_file == "/path/to/workflow.yml"
        assert config.github_token == "ghp_token123"
        assert config.no_warnings is True

    def test_config_fix_mode_enabled(self):
        """Test configuration for fix mode."""
        config = CLIConfig(fix=True)
        
        assert config.fix is True
        assert config.workflow_file is None  # Should work with all files
        assert config.github_token is None
        assert config.no_warnings is False

    def test_config_quiet_mode(self):
        """Test configuration for quiet mode (no warnings)."""
        config = CLIConfig(fix=False, no_warnings=True)
        
        assert config.fix is False
        assert config.workflow_file is None
        assert config.github_token is None
        assert config.no_warnings is True

    def test_config_single_file_mode(self):
        """Test configuration for single file validation."""
        config = CLIConfig(
            fix=False,
            workflow_file=".github/workflows/ci.yml"
        )
        
        assert config.fix is False
        assert config.workflow_file == ".github/workflows/ci.yml"
        assert config.github_token is None
        assert config.no_warnings is False

    def test_config_with_github_token(self):
        """Test configuration with GitHub token for API access."""
        config = CLIConfig(
            fix=False,
            github_token="ghp_abcdef123456"
        )
        
        assert config.fix is False
        assert config.workflow_file is None
        assert config.github_token == "ghp_abcdef123456"
        assert config.no_warnings is False

    def test_config_combined_modes(self):
        """Test configuration with multiple modes combined."""
        config = CLIConfig(
            fix=True,
            workflow_file="specific.yml",
            github_token="token",
            no_warnings=True
        )
        
        assert config.fix is True
        assert config.workflow_file == "specific.yml"
        assert config.github_token == "token"
        assert config.no_warnings is True

    def test_config_equality(self):
        """Test configuration equality comparison."""
        config1 = CLIConfig(fix=True, workflow_file="test.yml")
        config2 = CLIConfig(fix=True, workflow_file="test.yml")
        config3 = CLIConfig(fix=False, workflow_file="test.yml")
        
        assert config1 == config2  # Same values
        assert config1 != config3  # Different fix value

    def test_config_defaults(self):
        """Test that optional fields have correct defaults."""
        config = CLIConfig(fix=False)
        
        # Test default values match the dataclass definition
        assert config.workflow_file is None
        assert config.github_token is None
        assert config.no_warnings is False

    def test_config_boolean_types(self):
        """Test that boolean fields accept correct types."""
        # Test fix field
        config_fix_true = CLIConfig(fix=True)
        config_fix_false = CLIConfig(fix=False)
        
        assert config_fix_true.fix is True
        assert config_fix_false.fix is False
        
        # Test no_warnings field
        config_quiet = CLIConfig(fix=False, no_warnings=True)
        config_verbose = CLIConfig(fix=False, no_warnings=False)
        
        assert config_quiet.no_warnings is True
        assert config_verbose.no_warnings is False

    def test_config_optional_string_types(self):
        """Test that optional string fields accept None and strings."""
        # Test with None values
        config_none = CLIConfig(fix=False)
        assert config_none.workflow_file is None
        assert config_none.github_token is None
        
        # Test with string values
        config_strings = CLIConfig(
            fix=False,
            workflow_file="file.yml",
            github_token="token"
        )
        assert isinstance(config_strings.workflow_file, str)
        assert isinstance(config_strings.github_token, str)
