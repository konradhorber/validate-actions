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
    quiet: bool = typer.Option(default=False, help="Suppress warning-level problems in output"),
):
    """Main CLI entry point for validate-actions.
    
    Validates GitHub Actions workflow files, detecting configuration errors,
    typos, and best practice violations. Can automatically fix certain issues.
    
    Args:
        workflow_file: Path to a specific workflow file to validate. If not provided,
            searches for workflow files in .github/workflows/ directory.
        fix: Whether to automatically fix detected problems where possible.
        quiet: Whether to suppress warning-level problems from output, showing
            only errors.
            
    Environment Variables:
        GH_TOKEN: GitHub token for API access (optional for rate limits, esp. in testing)
        
    Examples:
        Validate all workflows:
            $ validate-actions
            
        Validate specific file:
            $ validate-actions .github/workflows/ci.yml
            
        Auto-fix issues:
            $ validate-actions --fix
            
        Quiet mode (errors only):
            $ validate-actions --quiet
    """
    config = CLIConfig(
        fix=fix, workflow_file=workflow_file, github_token=os.getenv("GH_TOKEN"), no_warnings=quiet
    )

    cli: CLI = StandardCLI(config)
    exit_code = cli.run()
    sys.exit(exit_code)
