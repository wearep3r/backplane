#!/usr/bin/env python3

import typer
import os
import subprocess
import yaml
import json
import re
from enum import Enum
import anyconfig

app = typer.Typer(help="backplane CLI")

@app.command()
def init():
  # Check if ~/.backplane exists
  backplane_config_dir = os.getenv("BACKPLANE_CONIG_DIR",os.path.join(os.getenv("HOME","~"),".backplane"))
  if not os.path.exists(backplane_config_dir):
    typer.secho(f"config directory {backplane_config_dir} does not exist", err=True, fg=typer.colors.RED)
    try:
        os.mkdir(backplane_config_dir)
    except OSError as e:
        typer.secho(f"config directory {backplane_config_dir} could not be created: {e}", err=True, fg=typer.colors.RED)
    else:
        typer.secho(f"config directory {backplane_config_dir} created", err=False, fg=typer.colors.GREEN)
  else:
    typer.secho(f"config directory {backplane_config_dir} exists", err=False, fg=typer.colors.GREEN)

  backplane_contexts_dir = os.getenv("BACKPLANE_CONTEXTS_DIR",os.path.join(backplane_config_dir,"contexts"))
  if not os.path.exists(backplane_contexts_dir):
    typer.secho(f"contexts directory {backplane_contexts_dir} does not exist", err=True, fg=typer.colors.RED)
    try:
        os.mkdir(backplane_contexts_dir)
    except OSError as e:
        typer.secho(f"contexts directory {backplane_contexts_dir} could not be created: {e}", err=True, fg=typer.colors.RED)
    else:
        typer.secho(f"contexts directory {backplane_contexts_dir} created", err=False, fg=typer.colors.GREEN)
  else:
    typer.secho(f"contexts directory {backplane_contexts_dir} exists", err=False, fg=typer.colors.GREEN)

  backplane_default_context_dir = os.getenv("BACKPLANE_DEFAULT_CONTEXT_DIR",os.path.join(backplane_contexts_dir,"default"))
  if not os.path.exists(backplane_default_context_dir):
    typer.secho(f"default context directory {backplane_default_context_dir} does not exist", err=True, fg=typer.colors.RED)
    try:
        os.mkdir(backplane_default_context_dir)
    except OSError as e:
        typer.secho(f"default context directory {backplane_default_context_dir} could not be created: {e}", err=True, fg=typer.colors.RED)
    else:
        typer.secho(f"default context directory {backplane_default_context_dir} created", err=False, fg=typer.colors.GREEN)
  else:
    typer.secho(f"default context directory {backplane_default_context_dir} exists", err=False, fg=typer.colors.GREEN)

@app.command()
def version():
    """
  Show apollo's version
  """

    version = os.getenv("APOLLO_VERSION")

    if not version:
        typer.secho(f"No version found", err=True, fg=typer.colors.RED)
        raise typer.Exit(code=1)

    typer.secho(f"{version}", err=False, fg=typer.colors.GREEN)
    return version

@app.callback()
def callback(
    verbosity: int = typer.Option(0, "--verbosity", "-v", help="Verbosity"),
    debug: bool = typer.Option(False, "--debug", "-d", help="Enable Debugging"),
    environment: str = typer.Option("development", "--environment", "-e", help="Environment"),
):
  typer.secho(f"Verbosity: {verbosity}", err=False, fg=typer.colors.GREEN)


if __name__ == "__main__":
    app()
