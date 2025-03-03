import cli
import typer



def main(file: str):
    cli.run(file)

    

if __name__ == "__main__":
    typer.run(main)