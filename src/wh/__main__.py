"""Entry point for running wh as a module: python -m wh"""

# Import wh first to set up reactor
import wh  # noqa: F401

from wh.cli.main import cli

if __name__ == "__main__":
    cli()
