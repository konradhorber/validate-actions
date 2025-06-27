import typer

from validate_actions.cli import CLI

app = typer.Typer()


@app.callback(invoke_without_command=True)
def main(
    workflow_file: str = typer.Argument(default=None, help="Path to a specific workflow file to validate"),
    fix: bool = typer.Option(default=False, help="Automatically fix some problems"),
):
    cli = CLI()
    cli.start(fix=fix, workflow_file=workflow_file)
