import yaml
import subprocess

def parse_yaml(file_path: str) -> dict:
    with open(file_path, 'r') as stream:
        try:
            return yaml.safe_load(stream) 
        except yaml.YAMLError as exc:
            print(exc)
            return

def has_trigger(workflow: dict):
    return 'on' in workflow or True in workflow # TODO: on is passed to true due to yaml standard

def has_jobs(workflow: dict):
    return 'jobs' in workflow


def run_yamllint(file_path: str) -> str:
    cmd = 'yamllint ' + file_path
    subprocess.run(cmd, shell=True)