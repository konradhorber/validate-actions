import yaml
import subprocess
import Issue

def parse_yaml(file_path: str) -> dict:
    with open(file_path, 'r') as stream:
        try:
            return yaml.safe_load(stream) 
        except yaml.YAMLError as exc:
            print(exc)
            return

def has_trigger(workflow: dict) -> Issue.Issue:
    keys_list = list(workflow.keys())
    trigger_index = None
    if True in keys_list:
        trigger_index = keys_list.index(True)
        return Issue.Issue(trigger_index+1, 0, 'error', 'should have trigger (on keyword)', 'trigger').__str__()        

def has_jobs(workflow: dict):
    print()
    # return 'jobs' in workflow


def run_yamllint(file_path: str) -> str:
    cmd = 'yamllint ' + file_path
    subprocess.run(cmd, shell=True)