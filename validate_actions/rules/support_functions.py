import yaml
from typing import Iterable
import logging
import requests
import json
import importlib.resources as pkg_resources

# TODO fix and upgrade this mess
def get_workflow_schema(file: str) -> dict:
    schema_path = pkg_resources.files(
        'validate_actions.resources'
    ).joinpath(file)
    with schema_path.open('r', encoding='utf-8') as f:
        return json.load(f)


def find_index_of(value: str, token_type: yaml.Token, tokens: list[yaml.Token]) -> Iterable[int]:
    for i, token in enumerate(tokens):
        if isinstance(token, token_type) and token.value == value:
            yield i

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
SESSION = requests.Session()
GITHUB_URL = 'https://raw.githubusercontent.com/'

same_session_cache = {}

def parse_action(slug):
    action, sep, tag = slug.partition('@')
    tags = [tag] if sep else ['main', 'master']

    for current_tag in tags:
        url_no_ext = f'{GITHUB_URL}{action}/{current_tag}/action'
        
        if url_no_ext in same_session_cache:
            return same_session_cache[url_no_ext]
        
        for ext in ['.yml', '.yaml']:
            try:
                response = SESSION.get(f'{url_no_ext}{ext}')
            except requests.RequestException as e:
                logger.warning(f"Request error for {url_no_ext}{ext}: {e}")
                continue
            
            if response.status_code == 200:
                try:
                    action_metadata = yaml.safe_load(response.text)
                except yaml.YAMLError as e:
                    logger.error(f"Couldn't parse YAML of {action} download: {e}")
                    return
                same_session_cache[url_no_ext] = action_metadata
                return action_metadata
    return
