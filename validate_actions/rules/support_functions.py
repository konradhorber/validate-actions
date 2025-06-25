import logging
from pathlib import Path
from typing import Dict, Iterable, Optional

import requests
import yaml

from validate_actions.problems import Problem, ProblemLevel
from validate_actions.workflow.ast import String

# TODO fix and upgrade this mess


def find_index_of(value: str, token_type: yaml.Token, tokens: list[yaml.Token]) -> Iterable[int]:
    for i, token in enumerate(tokens):
        if isinstance(token, token_type) and token.value == value:
            yield i


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
SESSION = requests.Session()
GITHUB_URL = "https://raw.githubusercontent.com/"

parse_action_cache = {}


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
            try:
                response = SESSION.get(f"{url_no_ext}{ext}")
            except requests.RequestException as e:
                logger.warning(f"Request error for {url_no_ext}{ext}: {e}")
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
    url = f"https://api.github.com/repos/{slug}/tags"
    if url in get_current_action_version_cache:
        return get_current_action_version_cache[url]

    try:
        response = SESSION.get(url)
    except requests.RequestException as e:
        logger.warning(f"Request error for {url}: {e}")

    if response.status_code == 200:
        try:
            tags = response.json()
            if tags:
                latest_tag = tags[0]["name"]
                get_current_action_version_cache[url] = latest_tag
                return latest_tag
        except (ValueError, KeyError) as e:
            logger.warning(f"Couldn't parse JSON response from {url}: {e}")

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

    except (OSError, ValueError, TypeError, UnicodeError):
        return problem
    finally:
        return problem
