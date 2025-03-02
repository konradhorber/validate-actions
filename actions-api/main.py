import typer
import yaml_parser
import json
from rich import print
from rich.console import Console
console = Console()


def main(workflow: str):
    dict = yaml_parser.parse_yaml(workflow)
    print(dict)

    console.print(workflow, style="underline")
    print(yaml_parser.has_trigger(dict))
    print(yaml_parser.has_jobs(dict))
    print(yaml_parser.run_yamllint(workflow))
    

if __name__ == "__main__":
    typer.run(main)