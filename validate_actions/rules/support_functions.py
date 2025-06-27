import logging
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple, Type

import requests
import yaml

from validate_actions.problems import Problem, ProblemLevel
from validate_actions.workflow.ast import String

# TODO fix and upgrade this mess


def find_index_of(
    value: str, token_type: Type[yaml.Token], tokens: list[yaml.Token]
) -> Iterable[int]:
    for i, token in enumerate(tokens):
        if isinstance(token, token_type) and hasattr(token, "value") and token.value == value:
            yield i


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
SESSION = requests.Session()
GITHUB_URL = "https://raw.githubusercontent.com/"
token = os.getenv("GH_TOKEN")
if token:
    SESSION.headers.update({"Authorization": f"token {token}"})

# Request timeout and retry configuration
REQUEST_TIMEOUT = 10  # seconds
MAX_RETRIES = 3
RETRY_BACKOFF_FACTOR = 1.5  # exponential backoff multiplier

parse_action_cache: Dict[str, Any] = {}
action_tags_cache: Dict[str, List[Dict]] = {}


def _make_request_with_retry(
    url: str, max_retries: int = MAX_RETRIES
) -> Optional[requests.Response]:
    """Make HTTP request with timeout and exponential backoff retry logic.

    Args:
        url: URL to request
        max_retries: Maximum number of retry attempts

    Returns:
        Response object if successful, None if all retries failed
    """
    for attempt in range(max_retries + 1):  # +1 for initial attempt
        try:
            response = SESSION.get(url, timeout=REQUEST_TIMEOUT)
            return response
        except (requests.RequestException, requests.Timeout) as e:
            if attempt < max_retries:  # Don't sleep after the last attempt
                sleep_time = RETRY_BACKOFF_FACTOR**attempt
                logger.debug(
                    f"Request failed (attempt {attempt + 1}/{max_retries + 1}): {e}. "
                    f"Retrying in {sleep_time:.1f}s..."
                )
                time.sleep(sleep_time)
            else:
                logger.warning(f"Request failed after {max_retries + 1} attempts for {url}: {e}")

    return None


def parse_semantic_version(version_str: str) -> Optional[Tuple[int, Optional[int], Optional[int]]]:
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


def compare_semantic_versions(
    current: Tuple[int, int, int], used: Tuple[int, int, int]
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
    if None in [current_major, current_minor, current_patch, used_major, used_minor, used_patch]:
        raise ValueError("Cannot compare partial versions. Use resolve_version_to_latest() first.")

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


def is_commit_sha(version_str: str) -> bool:
    """Check if a version string is a commit SHA.

    A commit SHA is a hex string of at least 7 characters.
    """
    if not version_str or len(version_str) < 7:
        return False

    # Check if all characters are hexadecimal
    return re.match(r"^[a-f0-9]+$", version_str.lower()) is not None


def get_action_tags(slug: str) -> List[Dict]:
    """Fetch all tags for an action from GitHub API with caching.

    Returns list of tag objects with 'name' and 'commit' fields.
    Returns empty list if unable to fetch or action doesn't exist.
    """
    if slug in action_tags_cache:
        return action_tags_cache[slug]

    url = f"https://api.github.com/repos/{slug}/tags"

    response = _make_request_with_retry(url)
    if response is not None and response.status_code == 200:
        try:
            tags = response.json()
            action_tags_cache[slug] = tags
            return tags
        except (ValueError, KeyError) as e:
            logger.warning(f"JSON parsing error for {url}: {e}")

    # Cache empty result to avoid repeated failed requests
    action_tags_cache[slug] = []
    return []


def resolve_version_to_latest(slug: str, partial_version: str) -> Optional[str]:
    """Resolve partial version like 'v4' to latest matching version like 'v4.2.2'.

    This handles the GitHub Actions semantic where "v4" means "latest v4.x.x".

    Args:
        slug: Action slug like 'actions/checkout'
        partial_version: Partial version like 'v4' or 'v4.2'

    Returns:
        Latest matching version string or None if not found
    """
    tags = get_action_tags(slug)
    if not tags:
        return None

    # Parse the partial version
    partial_parsed = parse_semantic_version(partial_version)
    if not partial_parsed:
        return None

    partial_major, partial_minor, partial_patch = partial_parsed

    # Find all tags that match the partial version pattern
    matching_versions = []
    for tag in tags:
        tag_name = tag.get("name", "")
        tag_parsed = parse_semantic_version(tag_name)
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
            if tag_major == partial_major and tag_minor == partial_minor and tag_patch is not None:
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


def parse_action(slug):
    if isinstance(slug, String):
        slug = slug.string
    action, sep, tag = slug.partition("@")
    tags = [tag] if sep else ["main", "master"]

    for current_tag in tags:
        url_no_ext = f"{GITHUB_URL}{action}/{current_tag}/action"

        if url_no_ext in parse_action_cache:
            return parse_action_cache[url_no_ext]

        for ext in [".yml", ".yaml"]:
            response = _make_request_with_retry(f"{url_no_ext}{ext}")
            if response is None:
                continue

            if response.status_code == 200:
                try:
                    action_metadata = yaml.safe_load(response.text)
                except yaml.YAMLError as e:
                    logger.error(f"Couldn't parse YAML of {action} download: {e}")
                    return
                parse_action_cache[url_no_ext] = action_metadata
                return action_metadata
    return


get_current_action_version_cache: Dict[str, str] = {}


def get_current_action_version(slug: str) -> Optional[str]:
    """Get the latest version tag for an action.

    This function now uses get_action_tags() internally to maintain DRY principles
    and benefit from the enhanced caching strategy.

    Args:
        slug: Action slug like 'actions/checkout'

    Returns:
        Latest version tag or None if not found
    """
    # Use the new get_action_tags function for consistency
    tags = get_action_tags(slug)
    if tags:
        return tags[0].get("name")
    return None


def edit_yaml_at_position(
    file_path: Path,
    idx: int,
    num_delete: int,
    new_text: str,
    problem: Problem,
    new_problem_desc: str,
) -> Problem:
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        if idx < 0 or idx >= len(content):
            return problem

        # Perform edit: delete and insert
        updated_content = content[:idx] + new_text + content[idx + num_delete :]

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(updated_content)

        problem.level = ProblemLevel.NON
        problem.desc = new_problem_desc
        return problem

    except (OSError, UnicodeError) as e:
        logger.warning(f"File operation error for {file_path}: {e}")
        return problem
