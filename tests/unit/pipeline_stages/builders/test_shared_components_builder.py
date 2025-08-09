"""Unit tests for shared components builder."""

from validate_actions.domain_model import ast
from validate_actions.domain_model.primitives import Pos
from validate_actions.globals.problems import Problems
from validate_actions.pipeline_stages.builders.shared_components_builder import (
    DefaultSharedComponentsBuilder,
)


class TestSharedComponentsBuilderEnv:
    """Unit tests for environment variable building."""

    def test_build_env_with_valid_string_values(self):
        """Test building environment with valid string values."""
        problems = Problems()
        builder = DefaultSharedComponentsBuilder(problems)

        env_vars = {
            ast.String("NODE_ENV", Pos(1, 1, 0)): ast.String("production", Pos(1, 11, 10)),
            ast.String("DEBUG", Pos(2, 1, 20)): ast.String("false", Pos(2, 8, 27)),
        }

        result = builder.build_env(env_vars)

        assert isinstance(result, ast.Env)
        assert len(result.variables) == 2
        assert problems.n_error == 0

    def test_build_env_with_boolean_values(self):
        """Test building environment with boolean values converted to strings."""
        problems = Problems()
        builder = DefaultSharedComponentsBuilder(problems)

        env_vars = {
            ast.String("DEBUG", Pos(1, 1, 0)): True,
            ast.String("VERBOSE", Pos(2, 1, 20)): False,
        }

        result = builder.build_env(env_vars)

        assert isinstance(result, ast.Env)
        assert len(result.variables) == 2
        assert result.variables[ast.String("DEBUG", Pos(1, 1, 0))].string == "true"
        assert result.variables[ast.String("VERBOSE", Pos(2, 1, 20))].string == "false"
        assert problems.n_error == 0

    def test_build_env_with_invalid_values_reports_errors(self):
        """Test that invalid environment values generate errors."""
        problems = Problems()
        builder = DefaultSharedComponentsBuilder(problems)

        env_vars = {ast.String("INVALID", Pos(1, 1, 0)): {"nested": "dict"}}

        result = builder.build_env(env_vars)

        assert result is None
        assert problems.n_error == 2  # Invalid value + No valid vars


class TestSharedComponentsBuilderPermissions:
    """Unit tests for permissions building."""

    def test_build_permissions_with_read_all_string(self):
        """Test building permissions with 'read-all' string."""
        problems = Problems()
        builder = DefaultSharedComponentsBuilder(problems)

        permissions = builder.build_permissions(ast.String("read-all", Pos(1, 1, 0)))

        assert isinstance(permissions, ast.Permissions)
        assert permissions.actions_ == ast.Permission.read
        assert permissions.contents_ == ast.Permission.read
        assert problems.n_error == 0

    def test_build_permissions_with_dict(self):
        """Test building permissions with dictionary format."""
        problems = Problems()
        builder = DefaultSharedComponentsBuilder(problems)

        permissions_dict = {
            ast.String("actions", Pos(1, 1, 0)): ast.String("read", Pos(1, 9, 8)),
            ast.String("contents", Pos(2, 1, 20)): ast.String("write", Pos(2, 11, 30)),
        }

        permissions = builder.build_permissions(permissions_dict)

        assert isinstance(permissions, ast.Permissions)
        assert permissions.actions_ == ast.Permission.read
        assert permissions.contents_ == ast.Permission.write
        assert problems.n_error == 0

    def test_build_permissions_with_invalid_permission_reports_error(self):
        """Test that invalid permission values generate errors."""
        problems = Problems()
        builder = DefaultSharedComponentsBuilder(problems)

        permissions_dict = {
            ast.String("actions", Pos(1, 1, 0)): ast.String("invalid", Pos(1, 9, 8))
        }

        permissions = builder.build_permissions(permissions_dict)

        assert isinstance(permissions, ast.Permissions)
        assert problems.n_error == 1


class TestSharedComponentsBuilderDefaults:
    """Unit tests for defaults building."""

    def test_build_defaults_with_valid_shell(self):
        """Test building defaults with valid shell configuration."""
        problems = Problems()
        builder = DefaultSharedComponentsBuilder(problems)

        defaults_dict = {
            ast.String("run", Pos(1, 1, 0)): {
                ast.String("shell", Pos(2, 1, 10)): ast.String("bash", Pos(2, 8, 17))
            }
        }

        result = builder.build_defaults(defaults_dict)

        assert isinstance(result, ast.Defaults)
        assert result.shell_ == ast.Shell.bash
        assert result.working_directory_ is None
        assert problems.n_error == 0

    def test_build_defaults_with_working_directory(self):
        """Test building defaults with working directory."""
        problems = Problems()
        builder = DefaultSharedComponentsBuilder(problems)

        defaults_dict = {
            ast.String("run", Pos(1, 1, 0)): {
                ast.String("working-directory", Pos(2, 1, 10)): ast.String("./src", Pos(2, 20, 29))
            }
        }

        result = builder.build_defaults(defaults_dict)

        assert isinstance(result, ast.Defaults)
        assert result.shell_ is None
        assert result.working_directory_.string == "./src"
        assert problems.n_error == 0

    def test_build_defaults_with_invalid_structure_reports_error(self):
        """Test that invalid defaults structure generates errors."""
        problems = Problems()
        builder = DefaultSharedComponentsBuilder(problems)

        # Invalid: missing 'run' key
        defaults_dict = {ast.String("invalid", Pos(1, 1, 0)): {}}

        result = builder.build_defaults(defaults_dict)

        assert result is None
        assert problems.n_error == 1
