import cli
import typer
from pathlib import Path



def main():
    directory = Path('.github-test/workflows')
    cli.run_directory(directory)


    

if __name__ == "__main__":
    typer.run(main)