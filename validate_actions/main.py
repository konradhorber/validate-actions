import validate_actions.cli as cli
import typer
from pathlib import Path


app = typer.Typer()

@app.callback(invoke_without_command=True)
def main():
    project_root = find_workflows()
    if not project_root:
        print(f'{cli.STYLE["neutral"]}Could not find workflows directory. Please run this script from the root of your project.{cli.STYLE["format_end"]}')
        raise typer.Exit(1)
    directory = project_root / '.github-test/workflows'
    cli.run_directory(directory)

def find_workflows(marker='.github-test'):
    start_dir = Path.cwd()
    for directory in [start_dir] + list(start_dir.parents)[:2]:
        if (directory / marker).is_dir():
            return directory
    return None

if __name__ == "__main__":
    app()