import os
import sys

import typer

from validate_actions.cli import CLI, StandardCLI
from validate_actions.globals.cli_config import CLIConfig

app = typer.Typer()


@app.callback(invoke_without_command=True)
def main(
    workflow_file: str = typer.Argument(
        default=None, help="Path to a specific workflow file to validate"
    ),
    fix: bool = typer.Option(default=False, help="Automatically fix some problems"),
):
    config = CLIConfig(fix=fix, workflow_file=workflow_file, github_token=os.getenv("GH_TOKEN"))

    cli: CLI = StandardCLI(config)
    exit_code = cli.run()
    sys.exit(exit_code)
