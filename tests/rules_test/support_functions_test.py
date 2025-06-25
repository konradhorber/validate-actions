"""
Tests for support functions used by the outdated version checking feature.
These test functions that will be implemented in support_functions.py
"""

from unittest.mock import Mock, patch

import pytest

from validate_actions.rules.support_functions import get_current_action_version


class TestTagFetching:
    """Test fetching tags from GitHub API"""

    def setup_method(self):
        """Clear cache before each test"""
        from validate_actions.rules.support_functions import (
            action_tags_cache,
            get_current_action_version_cache,
        )

        get_current_action_version_cache.clear()
        action_tags_cache.clear()

    def test_get_current_action_version_success(self):
        """Test successful tag fetching returns latest version"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"name": "v4.2.2"},
            {"name": "v4.2.1"},
            {"name": "v4.1.7"},
            {"name": "v4.0.0"},
            {"name": "v3.6.0"},
        ]

        with patch(
            "validate_actions.rules.support_functions.SESSION.get", return_value=mock_response
        ):
            latest = get_current_action_version("actions/checkout")
            assert latest == "v4.2.2"

    def test_api_rate_limit_returns_none(self):
        """Test API rate limit returns None gracefully"""
        mock_response = Mock()
        mock_response.status_code = 403

        with patch(
            "validate_actions.rules.support_functions.SESSION.get", return_value=mock_response
        ):
            result = get_current_action_version("actions/checkout")
            assert result is None

    def test_non_existent_repository_returns_none(self):
        """Test non-existent repository returns None"""
        mock_response = Mock()
        mock_response.status_code = 404

        with patch(
            "validate_actions.rules.support_functions.SESSION.get", return_value=mock_response
        ):
            result = get_current_action_version("non-existent/repo")
            assert result is None

    def test_empty_tags_returns_none(self):
        """Test empty tags list returns None"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = []

        with patch(
            "validate_actions.rules.support_functions.SESSION.get", return_value=mock_response
        ):
            result = get_current_action_version("actions/checkout")
            assert result is None

    def test_malformed_json_returns_none(self):
        """Test malformed JSON response returns None"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")

        with patch(
            "validate_actions.rules.support_functions.SESSION.get", return_value=mock_response
        ):
            result = get_current_action_version("actions/checkout")
            assert result is None


class TestVersionParsing:
    """Test semantic version parsing - functions to be implemented in support_functions.py"""

    def test_parse_full_semantic_version(self):
        """Test parsing full semantic versions"""
        from validate_actions.rules.support_functions import parse_semantic_version

        assert parse_semantic_version("v4.2.1") == (4, 2, 1)
        assert parse_semantic_version("4.2.1") == (4, 2, 1)
        assert parse_semantic_version("v1.10.5") == (1, 10, 5)

    def test_parse_partial_versions(self):
        """Test parsing versions with missing components - preserves None for safety"""
        from validate_actions.rules.support_functions import parse_semantic_version

        assert parse_semantic_version("v4.2") == (4, 2, None)
        assert parse_semantic_version("v4") == (4, None, None)
        assert parse_semantic_version("4") == (4, None, None)

    def test_parse_invalid_versions(self):
        """Test parsing invalid version strings"""
        from validate_actions.rules.support_functions import parse_semantic_version

        assert parse_semantic_version("release-2023") is None
        assert parse_semantic_version("latest") is None
        assert parse_semantic_version("main") is None
        assert parse_semantic_version("v4.2.1.0") is None
        assert parse_semantic_version("") is None
        assert parse_semantic_version("v") is None


class TestVersionComparison:
    """Test version comparison logic - functions to be implemented in support_functions.py"""

    def test_major_version_outdated(self):
        """Test major version differences"""
        from validate_actions.rules.support_functions import compare_semantic_versions

        assert compare_semantic_versions((4, 2, 1), (3, 6, 0)) == "major"
        assert compare_semantic_versions((5, 0, 0), (4, 9, 9)) == "major"

    def test_minor_version_outdated(self):
        """Test minor version differences"""
        from validate_actions.rules.support_functions import compare_semantic_versions

        assert compare_semantic_versions((4, 2, 1), (4, 1, 0)) == "minor"
        assert compare_semantic_versions((4, 5, 0), (4, 3, 2)) == "minor"

    def test_patch_version_outdated(self):
        """Test patch version differences"""
        from validate_actions.rules.support_functions import compare_semantic_versions

        assert compare_semantic_versions((4, 2, 2), (4, 2, 1)) == "patch"
        assert compare_semantic_versions((4, 2, 5), (4, 2, 0)) == "patch"

    def test_current_version_no_warning(self):
        """Test current version returns None"""
        from validate_actions.rules.support_functions import compare_semantic_versions

        assert compare_semantic_versions((4, 2, 1), (4, 2, 1)) is None
        assert compare_semantic_versions((1, 0, 0), (1, 0, 0)) is None

    def test_future_version_no_warning(self):
        """Test future version returns None"""
        from validate_actions.rules.support_functions import compare_semantic_versions

        assert compare_semantic_versions((4, 2, 1), (5, 0, 0)) is None
        assert compare_semantic_versions((4, 2, 1), (4, 3, 0)) is None
        assert compare_semantic_versions((4, 2, 1), (4, 2, 2)) is None


class TestCommitShaDetection:
    """Test commit SHA detection - functions to be implemented in support_functions.py"""

    def test_commit_sha_detection(self):
        """Test detection of commit SHAs"""
        from validate_actions.rules.support_functions import is_commit_sha

        assert is_commit_sha("11bd71901bbe5b1630ceea73d27597364c9af683") is True
        assert is_commit_sha("11bd719") is True  # Short SHA
        assert is_commit_sha("8e5e7e5ab8b370d6c329ec480221332ada57f0ab") is True

    def test_non_commit_sha_detection(self):
        """Test detection of non-SHA strings"""
        from validate_actions.rules.support_functions import is_commit_sha

        assert is_commit_sha("v4.2.1") is False
        assert is_commit_sha("main") is False
        assert is_commit_sha("release-2023") is False
        assert is_commit_sha("") is False
        assert is_commit_sha("123") is False  # Too short


class TestGetActionTags:
    """Test get_action_tags function - to be implemented in support_functions.py"""

    def setup_method(self):
        """Clear cache before each test"""
        from validate_actions.rules.support_functions import (
            action_tags_cache,
            get_current_action_version_cache,
        )

        get_current_action_version_cache.clear()
        action_tags_cache.clear()

    def test_get_action_tags_returns_all_tags(self):
        """Test getting all tags for an action"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"name": "v4.2.2", "commit": {"sha": "abc123"}},
            {"name": "v4.2.1", "commit": {"sha": "def456"}},
            {"name": "v4.1.7", "commit": {"sha": "ghi789"}},
        ]

        with patch(
            "validate_actions.rules.support_functions.SESSION.get", return_value=mock_response
        ):
            from validate_actions.rules.support_functions import get_action_tags

            tags = get_action_tags("actions/checkout")
            assert len(tags) == 3
            assert tags[0]["name"] == "v4.2.2"

    def test_resolve_partial_version_to_latest(self):
        """Test resolving partial versions like v4 to latest v4.x.x"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"name": "v4.2.2"},
            {"name": "v4.2.1"},
            {"name": "v4.1.7"},
            {"name": "v4.0.0"},
            {"name": "v3.6.0"},
        ]

        with patch(
            "validate_actions.rules.support_functions.SESSION.get", return_value=mock_response
        ):
            from validate_actions.rules.support_functions import resolve_version_to_latest

            # v4 should resolve to v4.2.2, not v4.0.0
            resolved = resolve_version_to_latest("actions/checkout", "v4")
            assert resolved == "v4.2.2"


@pytest.mark.slow
class TestRealGitHubAPI:
    """Integration tests with real GitHub API (run sparingly)"""

    def test_real_actions_checkout_version(self):
        """Test getting real version for actions/checkout"""
        version = get_current_action_version("actions/checkout")
        assert version is not None
        assert version.startswith("v")

    def test_private_repo_returns_none(self):
        """Test that private/non-existent repos return None"""
        version = get_current_action_version("private-org/private-repo")
        assert version is None
