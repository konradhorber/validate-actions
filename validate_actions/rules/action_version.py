"""Validates version specifications in workflow action 'uses:' fields."""
import re
from typing import Generator, List, Optional, Tuple

import requests

from validate_actions.domain_model.ast import ExecAction
from validate_actions.globals.problems import Problem, ProblemLevel
from validate_actions.rules.rule import Rule


class ActionVersion(Rule):
    """Validates the version specifications in workflow action 'uses:' fields.

    This rule checks GitHub Actions workflow steps that reference external actions
    via the 'uses:' field. It validates version specifications and checks for outdated
    versions.

    Key validations:
    - Warns when actions don't specify version tags
    - Detects outdated action versions (supports semantic versioning and commit SHAs)
    - Provides auto-fix capabilities for version updates
    """

    NAME = "action-version"

    # ====================
    # MAIN VALIDATION METHODS
    # ====================

    def check(self) -> Generator[Problem, None, None]:
        """Validates all actions in the workflow for version issues.

        Iterates through all workflow jobs and their steps, collecting
        ExecAction instances (steps that use the 'uses:' field) and
        validates them for version specifications.

        Yields:
            Problem: Problems found during validation including version
                warnings and outdated version issues.
        """
        actions = []
        for job in self.workflow.jobs_.values():
            steps = job.steps_
            for step in steps:
                if isinstance(step.exec, ExecAction):
                    actions.append(step.exec)
        return self._check_single_action(actions)

    def _check_single_action(
        self,
        actions: List[ExecAction],
    ) -> Generator[Problem, None, None]:
        """Validates each action individually for version issues.

        Processes each ExecAction to check version specifications.

        Args:
            actions: List of ExecAction instances to validate.

        Yields:
            Problem: Problems found including version warnings and outdated versions.
        """
        for action in actions:
            yield from self._not_using_version_spec(action)
            yield from self._is_outdated_version(action)

    # ====================
    # VERSION VALIDATION METHODS
    # ====================

    def _not_using_version_spec(self, action: ExecAction) -> Generator[Problem, None, None]:
        """Checks if an action specifies a version using '@version'.

        GitHub Actions best practices recommend pinning actions to specific versions
        rather than using default branches. This method warns when no version is
        specified and can auto-fix by adding the latest available version.

        Args:
            action: The ExecAction to validate for version specification.

        Yields:
            Problem: Warning if no version is specified, with optional auto-fix.
        """
        slug = action.uses_.string
        if "@" not in slug or not slug.split("@", 1)[1]:  # Check if there's no version spec
            # Check if (1) there is no '@' or (2) if the part after '@' is empty
            latest_version = self._get_current_action_version(action)
            version_suggestion = f"@{latest_version}" if latest_version else "@version"

            problem = Problem(
                action.pos,
                ProblemLevel.WAR,
                f"Using specific version of {slug} is recommended. "
                f"Consider using {slug}{version_suggestion}",
                self.NAME,
            )
            problem = self._fix_not_using_version_spec(action, slug, problem)
            yield problem

    def _is_outdated_version(self, action: ExecAction) -> Generator[Problem, None, None]:
        """
        Checks if an action is using an outdated version and generates warnings.

        Handles full versions (v4.2.1), partial versions (v4), and commit SHAs.
        Uses GitHub Actions semantics where 'v4' resolves to latest 'v4.x.x'.

        Args:
            action (ExecAction): The action to validate.

        Yields:
            Problem: Warning if version is outdated, with auto-fix support.
        """
        slug = action.uses_.string

        # Skip actions without version specs - handled by not_using_version_spec
        if "@" not in slug:
            return
        action_slug, version_spec = slug.rsplit("@", 1)
        # Skip empty version specs
        if not version_spec:
            return

        try:
            # Get the current latest version for this action
            current_latest = self._get_current_action_version(action)
            if not current_latest:
                # Can't check if we can't fetch action metadata (e.g., private repo)
                return

            # Parse the current latest version
            current_parsed = self._parse_semantic_version(current_latest)
            if not current_parsed or None in current_parsed:
                # Current version is not a valid semantic version
                return

            # Convert to complete tuple for comparison
            current_tuple = self._ensure_complete_version_tuple(current_parsed)

            # Handle different version spec types
            if self._is_commit_sha(version_spec):
                # Handle commit SHA by finding its corresponding version
                yield from self._handle_commit_sha_version(
                    action, action_slug, version_spec, current_latest, current_tuple
                )
            else:
                # Handle semantic version (partial or full)
                yield from self._handle_semantic_version(
                    action, action_slug, version_spec, current_latest, current_tuple
                )

        except (requests.RequestException, ValueError, TypeError, IndexError):
            # Graceful handling of expected errors during version checking
            # Network issues, parsing errors, or malformed version data
            return

    # ====================
    # UTILITY METHODS
    # ====================

    def _get_current_action_version(self, action: ExecAction) -> Optional[str]:
        """Retrieves the latest version tag for an action from its metadata.

        Args:
            action: The ExecAction containing metadata with version information.

        Returns:
            The name of the latest version tag, or None if no version data available.
        """
        if (
            action.metadata is not None
            and action.metadata.version_tags is not None
            and isinstance(action.metadata.version_tags, list)
            and len(action.metadata.version_tags) > 0
        ):
            return action.metadata.version_tags[0].get("name")
        return None

    def _parse_semantic_version(
        self, version_str: str
    ) -> Optional[Tuple[int, Optional[int], Optional[int]]]:
        """Parse semantic version string into tuple with explicit None for missing components.

        This function parses exactly what's provided without making assumptions.
        For GitHub Actions version resolution, use resolve_version_to_latest().

        Examples:
            "v4.2.1" -> (4, 2, 1)      # Full version
            "v4.2"   -> (4, 2, None)   # Minor specified, patch missing
            "v4"     -> (4, None, None) # Only major specified
            "invalid" -> None           # Parse error

        WARNING: Do not assume None means 0! Use resolve_version_to_latest()
        for GitHub Actions semantics where "v4" means "latest v4.x.x".
        """
        if not version_str:
            return None

        # Remove 'v' prefix if present
        version_str = version_str.lstrip("v")

        # Split on dots and validate
        parts = version_str.split(".")
        if len(parts) > 3:
            return None

        try:
            # Parse only the parts that were explicitly provided
            major = int(parts[0]) if len(parts) > 0 else None
            minor = int(parts[1]) if len(parts) > 1 else None
            patch = int(parts[2]) if len(parts) > 2 else None

            # Must have at least major version
            if major is None:
                return None

            return (major, minor, patch)
        except (ValueError, IndexError):
            return None

    def _ensure_complete_version_tuple(
        self, parsed_version: Tuple[int, Optional[int], Optional[int]]
    ) -> Tuple[int, int, int]:
        """Converts a parsed version tuple to a complete tuple with no None values.

        Args:
            parsed_version: A version tuple that may contain None values.

        Returns:
            A complete version tuple with 0 substituted for None values.

        Raises:
            ValueError: If the major version component is None.
        """
        major, minor, patch = parsed_version
        if major is None:
            raise ValueError("Major version cannot be None")
        return (major, minor or 0, patch or 0)

    def _is_commit_sha(self, version_str: str) -> bool:
        """Check if a version string is a commit SHA.

        A commit SHA is a hex string of at least 7 characters.
        """
        if not version_str or len(version_str) < 7:
            return False

        # Check if all characters are hexadecimal
        return re.match(r"^[a-f0-9]+$", version_str.lower()) is not None

    def _compare_semantic_versions(
        self, current: Tuple[int, int, int], used: Tuple[int, int, int]
    ) -> Optional[str]:
        """Compare two FULLY RESOLVED semantic version tuples.

        WARNING: Both versions must be fully resolved (no None components).
        Use resolve_version_to_latest() first for partial versions like "v4".

        Args:
            current: The current/latest version tuple (must be complete)
            used: The version being used (must be complete)

        Returns:
            "major" if major version is outdated
            "minor" if minor version is outdated
            "patch" if patch version is outdated
            None if used version is current or newer
        """
        current_major, current_minor, current_patch = current
        used_major, used_minor, used_patch = used

        # Validate that we have complete versions
        if None in [
            current_major,
            current_minor,
            current_patch,
            used_major,
            used_minor,
            used_patch,
        ]:
            raise ValueError(
                "Cannot compare partial versions. Use resolve_version_to_latest() first."
            )

        # Check if used version is newer or equal
        if (used_major, used_minor, used_patch) >= (current_major, current_minor, current_patch):
            return None

        # Check outdated level
        if used_major < current_major:
            return "major"
        elif used_minor < current_minor:
            return "minor"
        elif used_patch < current_patch:
            return "patch"

        return None

    def _resolve_version_to_latest(
        self, action: ExecAction, partial_version: str
    ) -> Optional[str]:
        """Resolves partial version like 'v4' to latest matching version like 'v4.2.2'.

        This handles the GitHub Actions semantic where "v4" means "latest v4.x.x".
        Uses the action's metadata to find all available version tags and returns
        the highest semantic version that matches the partial specification.

        Args:
            action: ExecAction containing metadata with available version tags.
            partial_version: Partial version specification like 'v4' or 'v4.2'.

        Returns:
            Latest matching version string or None if not found.
        """
        tags = action.metadata.version_tags if action.metadata else None
        if not tags or len(tags) == 0:
            return None

        # Parse the partial version
        partial_parsed = self._parse_semantic_version(partial_version)
        if not partial_parsed:
            return None

        partial_major, partial_minor, partial_patch = partial_parsed

        # Find all tags that match the partial version pattern
        matching_versions = []
        for tag in tags:
            tag_name = tag.get("name", "")
            tag_parsed = self._parse_semantic_version(tag_name)
            if not tag_parsed:
                continue

            tag_major, tag_minor, tag_patch = tag_parsed

            # Skip if any components are None (tag is also partial)
            if tag_major is None:
                continue

            # Match based on how many components were specified in partial_version
            if partial_minor is None:  # e.g., "v4" - match any v4.x.x
                if tag_major == partial_major and tag_minor is not None and tag_patch is not None:
                    matching_versions.append(((tag_major, tag_minor, tag_patch), tag_name))
            elif partial_patch is None:  # e.g., "v4.2" - match any v4.2.x
                if (
                    tag_major == partial_major
                    and tag_minor == partial_minor
                    and tag_patch is not None
                ):
                    matching_versions.append(((tag_major, tag_minor, tag_patch), tag_name))
            else:  # Full version - return exact match
                if (
                    tag_major == partial_major
                    and tag_minor == partial_minor
                    and tag_patch == partial_patch
                ):
                    return tag_name

        # Return the highest version among matches
        if matching_versions:
            matching_versions.sort(reverse=True, key=lambda x: x[0])  # Sort by version tuple
            return matching_versions[0][1]  # Return tag name

        return None

    # ====================
    # VERSION HANDLING METHODS
    # ====================

    def _handle_commit_sha_version(
        self,
        action: ExecAction,
        action_slug: str,
        commit_sha: str,
        current_latest: str,
        current_tuple: Tuple[int, int, int],
    ) -> Generator[Problem, None, None]:
        """Handle version checking for commit SHA specifications."""
        # Get all tags to find which version this commit corresponds to
        tags = action.metadata.version_tags if action.metadata else None
        if not tags or len(tags) == 0:
            return

        # Find the tag that matches this commit SHA
        commit_version = None
        # Ensure minimum meaningful SHA length for matching
        if len(commit_sha) < 7:
            return

        for tag in tags:
            tag_commit = tag.get("commit", {}).get("sha", "")
            # Only match if the tag's commit starts with our SHA (prefix match)
            # Require at least 7 characters for confident matching
            if tag_commit and tag_commit.startswith(commit_sha):
                commit_version = tag.get("name")
                break

        if not commit_version:
            # Unknown commit, generate warning with generic message
            problem = Problem(
                action.pos,
                ProblemLevel.WAR,
                f"Action {action_slug} uses commit SHA which may be outdated. "
                f"Current latest version is {current_latest}. Consider using versioned tags.",
                self.NAME,
            )
            problem = self._fix_commit_sha_version(
                action, action_slug, commit_sha, current_latest, problem
            )
            yield problem
            return

        # Parse the commit's corresponding version
        commit_parsed = self._parse_semantic_version(commit_version)
        if not commit_parsed or None in commit_parsed:
            return

        # Convert to complete tuple for comparison
        commit_tuple = self._ensure_complete_version_tuple(commit_parsed)

        # Compare versions
        outdated_level = self._compare_semantic_versions(current_tuple, commit_tuple)
        if outdated_level:
            problem = Problem(
                action.pos,
                ProblemLevel.WAR,
                f"Action {action_slug} uses commit SHA "
                f"(corresponds to {commit_version}) which is {outdated_level} "
                f"version outdated. Current latest is {current_latest}.",
                self.NAME,
            )
            problem = self._fix_outdated_commit_sha_version(
                action, action_slug, commit_sha, current_latest, problem
            )
            yield problem

    def _handle_semantic_version(
        self,
        action: ExecAction,
        action_slug: str,
        version_spec: str,
        current_latest: str,
        current_tuple: Tuple[int, int, int],
    ) -> Generator[Problem, None, None]:
        """Handle version checking for semantic version specifications."""
        # Parse the used version spec
        used_parsed = self._parse_semantic_version(version_spec)
        if not used_parsed:
            # Invalid version format, skip
            return

        # Check if this is a partial version that needs resolution
        if None in used_parsed:
            # Resolve partial version (e.g., v4 -> v4.2.2)
            resolved_version = self._resolve_version_to_latest(action, version_spec)
            if not resolved_version:
                # Version spec cannot be resolved - this is a problem!
                # E.g., actions/cache@v2 when only v3+ exists
                problem = Problem(
                    action.pos,
                    ProblemLevel.WAR,
                    f"Action {action_slug} uses outdated {version_spec} which "
                    f"cannot be resolved to any available version. "
                    f"Current latest is {current_latest}.",
                    self.NAME,
                )
                problem = self._fix_unresolvable_version(
                    action, action_slug, version_spec, current_latest, problem
                )
                yield problem
                return

            # Parse the resolved version
            resolved_parsed = self._parse_semantic_version(resolved_version)
            if not resolved_parsed or None in resolved_parsed:
                return

            # Convert to complete tuple for comparison
            resolved_tuple = self._ensure_complete_version_tuple(resolved_parsed)

            # For partial versions, compare the resolved version
            outdated_level = self._compare_semantic_versions(current_tuple, resolved_tuple)
            if outdated_level:
                problem = Problem(
                    action.pos,
                    ProblemLevel.WAR,
                    f"Action {action_slug} uses {version_spec} "
                    f"(resolves to {resolved_version}) which is {outdated_level} "
                    f"version outdated. Current latest is {current_latest}.",
                    self.NAME,
                )
                problem = self._fix_outdated_partial_version(
                    action, action_slug, version_spec, current_latest, problem
                )
                yield problem
        else:
            # Full version specification - validate it's complete
            if None in used_parsed:
                # This shouldn't happen for full versions, but safety check
                return

            # Convert to complete tuple for comparison
            full_tuple = self._ensure_complete_version_tuple(used_parsed)

            # Compare versions
            outdated_level = self._compare_semantic_versions(current_tuple, full_tuple)
            if outdated_level:
                problem = Problem(
                    action.pos,
                    ProblemLevel.WAR,
                    f"Action {action_slug} uses {version_spec} which is "
                    f"{outdated_level} version outdated. Current latest is {current_latest}.",
                    self.NAME,
                )
                problem = self._fix_outdated_full_version(
                    action, action_slug, version_spec, current_latest, problem
                )
                yield problem

    # ====================
    # FIXING METHODS
    # ====================

    def _fix_not_using_version_spec(
        self, action: ExecAction, slug: str, problem: Problem
    ) -> Problem:
        """Fix missing version specification by adding latest version."""
        version = self._get_current_action_version(action)
        if version:
            new_slug = f"{slug}@{version}"
            problem = self.fixer.edit_yaml_at_position(
                action.uses_.pos.idx,
                slug,
                new_slug,
                problem,
                f"Fixed '{slug}' to include version to '{new_slug}'",
            )
            action.uses_.string = f"{slug}@{version}"
        return problem

    def _fix_commit_sha_version(
        self,
        action: ExecAction,
        action_slug: str,
        commit_sha: str,
        current_latest: str,
        problem: Problem,
    ) -> Problem:
        """Fix commit SHA version by updating to latest version."""
        problem = self.fixer.edit_yaml_at_position(
            action.uses_.pos.idx + len(action_slug) + 1,  # +1 for '@'
            commit_sha,
            current_latest,
            problem,
            f"Updated commit SHA to latest version {current_latest}",
        )
        action.uses_.string = f"{action_slug}@{current_latest}"
        return problem

    def _fix_outdated_commit_sha_version(
        self,
        action: ExecAction,
        action_slug: str,
        commit_sha: str,
        current_latest: str,
        problem: Problem,
    ) -> Problem:
        """Fix outdated commit SHA version by updating to latest version."""
        problem = self.fixer.edit_yaml_at_position(
            action.uses_.pos.idx + len(action_slug) + 1,  # +1 for '@'
            commit_sha,
            current_latest,
            problem,
            f"Updated outdated commit SHA to latest version {current_latest}",
        )
        action.uses_.string = f"{action_slug}@{current_latest}"
        return problem

    def _fix_unresolvable_version(
        self,
        action: ExecAction,
        action_slug: str,
        version_spec: str,
        current_latest: str,
        problem: Problem,
    ) -> Problem:
        """Fix unresolvable version by updating to latest version."""
        problem = self.fixer.edit_yaml_at_position(
            action.uses_.pos.idx + len(action_slug) + 1,  # +1 for '@'
            version_spec,
            current_latest,
            problem,
            f"Fixed unresolvable version {version_spec} to latest {current_latest}",
        )
        action.uses_.string = f"{action_slug}@{current_latest}"
        return problem

    def _fix_outdated_partial_version(
        self,
        action: ExecAction,
        action_slug: str,
        version_spec: str,
        current_latest: str,
        problem: Problem,
    ) -> Problem:
        """Fix outdated partial version by updating to latest version."""
        problem = self.fixer.edit_yaml_at_position(
            action.uses_.pos.idx + len(action_slug) + 1,  # +1 for '@'
            version_spec,
            current_latest,
            problem,
            f"Fixed outdated version {version_spec} to latest {current_latest}",
        )
        action.uses_.string = f"{action_slug}@{current_latest}"
        return problem

    def _fix_outdated_full_version(
        self,
        action: ExecAction,
        action_slug: str,
        version_spec: str,
        current_latest: str,
        problem: Problem,
    ) -> Problem:
        """Fix outdated full version by updating to latest version."""
        problem = self.fixer.edit_yaml_at_position(
            action.uses_.pos.idx + len(action_slug) + 1,  # +1 for '@'
            version_spec,
            current_latest,
            problem,
            f"Fixed outdated version {version_spec} to latest {current_latest}",
        )
        action.uses_.string = f"{action_slug}@{current_latest}"
        return problem
