import typer
import yaml_parser
import json


def main(workflow: str):
    dict = yaml_parser.parse_yaml(workflow)
    print(json.dumps(dict, indent=2))

    print(yaml_parser.has_trigger(dict))
    print(yaml_parser.has_jobs(dict))
    print(yaml_parser.run_yamllint(workflow))
    

if __name__ == "__main__":
    typer.run(main)