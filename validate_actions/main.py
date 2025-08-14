"""Main CLI entry point for validate-actions."""

import os
import sys

import typer
from dotenv import load_dotenv

from validate_actions.cli import CLI, StandardCLI
from validate_actions.globals.cli_config import CLIConfig

load_dotenv()
app = typer.Typer()


@app.callback(invoke_without_command=True)
def main(
    workflow_file: str = typer.Argument(
        default=None, help="Path to a specific workflow file to validate"
    ),
    fix: bool = typer.Option(default=False, help="Automatically fix some problems"),
    quiet: bool = typer.Option(default=False, help="Suppress warning-level problems in output"),
    max_warnings: int = typer.Option(
        default=sys.maxsize,
        help="Maximum number of warnings before exiting with error",
        min=0,
        show_default=False,
    ),
):
    """Validates GitHub Actions workflow files. \n
    Detects YAML syntax, Actions schema errors, marketplace action use issues, and workflow
    execution path problems.
    """
    config = CLIConfig(
        fix=fix,
        max_warnings=max_warnings,
        workflow_file=workflow_file,
        github_token=os.getenv("GH_TOKEN"),
        no_warnings=quiet,
    )

    cli: CLI = StandardCLI(config)
    exit_code = cli.run()
    sys.exit(exit_code)
