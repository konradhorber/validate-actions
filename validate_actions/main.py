import typer

from validate_actions.cli import CLI

app = typer.Typer()


@app.callback(invoke_without_command=True)
def main(
    fix: bool = typer.Option(default=False, help="Automatically fix some problems"),
):
    cli = CLI()
    cli.start(fix=fix)
