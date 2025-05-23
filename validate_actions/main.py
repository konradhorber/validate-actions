import typer

from validate_actions.cli import CLI

app = typer.Typer()


@app.callback(invoke_without_command=True)
def main():
    cli = CLI()
    cli.start()


if __name__ == "__main__":
    app()
