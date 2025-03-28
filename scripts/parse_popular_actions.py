import json
import yaml
import logging
import requests
from pathlib import Path
from typing import Dict, Any, List

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

JSON_FILE = Path('scripts/popular_actions_in.json')
OUTPUT_FILE = Path('validate_actions/resources/popular_actions.json')
GITHUB_URL = 'https://raw.githubusercontent.com/'

def parse_action_file(action: Dict[str, Any], tag: str, session: requests.Session) -> Dict[str, Any]:
    """
    Fetches and parses a YAML file for a given action and tag from GitHub.
    
    :param action: Dictionary containing action details.
    :param tag: Git tag or branch to fetch the file from.
    :param session: Requests session for making HTTP requests.
    :return: Parsed YAML content as a dictionary.
    """
    slug = action['slug']
    path = action.get('path', 'action')
    file_ext = action.get('file_ext', 'yml')
    action_url = f'{GITHUB_URL}{slug}/{tag}/{path}.{file_ext}'
    
    try:
        response = session.get(action_url)
        response.raise_for_status()
    except requests.exceptions.RequestException as err:
        logger.error("Error while requesting action from web: %s", err)
        raise
    return yaml.safe_load(response.text)

def get_inputs(action_dict: Dict[str, Any]) -> Dict[str, bool]:
    """
    Extracts input definitions from the action dictionary.
    
    :param action_dict: Parsed YAML dictionary for the action.
    :return: A dictionary mapping each input parameter to whether it's required.
    """
    inputs = {}
    for param, attr in action_dict.get('inputs', {}).items():
        inputs[param] = bool(attr.get('required', False))
    return inputs

def get_outputs(action_dict: Dict[str, Any]) -> List[str]:
    """
    Extracts output definitions from the action dictionary.
    
    :param action_dict: Parsed YAML dictionary for the action.
    :return: A list of output keys.
    """
    outputs = []
    if 'outputs' not in action_dict:
        return outputs
    
    for return_value in action_dict['outputs']:
        outputs.append(return_value)
    return outputs

def main() -> None:
    popular_actions = {}
    session = requests.Session()

    with JSON_FILE.open() as f:
        json_popular_actions = json.load(f)

    for action in json_popular_actions:
        for tag in action['tags']:
            try:
                parsed_action = parse_action_file(action, tag, session)
            except requests.exceptions.RequestException:
                continue
            key = f"{action['slug']}@{tag}"
            popular_actions[key] = {
                "inputs": get_inputs(parsed_action),
                "outputs": get_outputs(parsed_action)
            }
    
    with OUTPUT_FILE.open('w') as f:
        json.dump(popular_actions, f, indent=4)
    logger.info("Successfully wrote popular actions to %s", OUTPUT_FILE)

if __name__ == "__main__":
    main()