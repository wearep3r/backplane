#!/usr/bin/env python3

import typer
import os
import subprocess
import yaml
import json
import re
from enum import Enum
import anyconfig
from dotenv import load_dotenv
import docker

app = typer.Typer(help="backplane CLI")

# Load .env file
load_dotenv()

docker_client = docker.from_env()

backplane_verbosity = 0
backplane_environment = os.getenv("BACKPLANE_ENVIRONMENT","development")
backplane_config_dir = os.getenv("BACKPLANE_CONIG_DIR",os.path.join(os.getenv("HOME","~"),".backplane"))
backplane_contexts_dir = os.getenv("BACKPLANE_CONTEXTS_DIR",os.path.join(backplane_config_dir,"contexts"))
backplane_default_context_dir = os.getenv("BACKPLANE_DEFAULT_CONTEXT_DIR",os.path.join(backplane_contexts_dir,"default"))
backplane_active_context_dir = backplane_default_context_dir

@app.command()
def init():
  # Check for Docker
  from shutil import which

  if not which("docker"):
    typer.secho(f"Docker not installed", err=True, fg=typer.colors.RED)

  if not which("docker-compose"):
    typer.secho(f"docker-compose not installed", err=True, fg=typer.colors.RED)

  # backplane_config_dir
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

  # backplane_contexts_dir
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

  # backplane_default_context_dir
  if not os.path.exists(backplane_default_context_dir):
    typer.secho(f"default context directory {backplane_default_context_dir} does not exist", err=True, fg=typer.colors.RED)
    
    try:
      backplane_repo = os.getenv("BACKPLANE_REPOSITORY","git@gitlab.com:p3r.one/backplane.git")
      clone_command = f"git clone {backplane_repo} {backplane_default_context_dir}"
      clone = subprocess.call(clone_command, shell=True)
      typer.secho(f"Successfully cloned {backplane_repo} to {backplane_default_context_dir}", err=False, fg=typer.colors.GREEN)
    except Exception as e:
      typer.secho(f"Failed to clone backplane repository from {backplane_repo} to {backplane_default_context_dir}: {e}", err=True, fg=typer.colors.RED)

      if verbosity > 0:
          typer.secho(f"{clone_command}", err=False, fg=typer.colors.BRIGHT_BLACK)

      raise typer.Exit(code=1)
  else:
    typer.secho(f"default context directory {backplane_default_context_dir} exists", err=False, fg=typer.colors.GREEN)

  # Make sure Docker network "backplane" exists
  backplane_network_exists = False
  docker_networks = docker_client.networks.list(names="backplane")

  for network in docker_networks:
    if network.name == "backplane":
      if "provider" in network.attrs['Labels'].keys():
        if network.attrs['Labels']['provider'] == "backplane":
          backplane_network_exists = True

  if not backplane_network_exists:
    try:
      backplane_network = docker_client.networks.create(name="backplane",check_duplicate=True,labels={"provider": "backplane"},attachable=True)
      typer.secho(f"Successfully created backplane Docker network", err=False, fg=typer.colors.GREEN)
    except Exception as e:
      typer.secho(f"Failed to create backplane Docker network: {e}", err=True, fg=typer.colors.RED)
  else:
    typer.secho(f"backplane Docker network exists", err=False, fg=typer.colors.GREEN)

@app.command()
def start(
    services: str = typer.Option('traefik,portainer', "--service", "-s", help="Backplane Service"),
  ):
  services = services.split(",")

  for service in services:
    try:
      docker_compose_command = f"ls -la; docker-compose -f docker-compose.yml -p backplane-{service} up -d"

      if backplane_verbosity > 0:
        typer.secho(f"{docker_compose_command}", err=False, fg=typer.colors.BRIGHT_BLACK)

      started = subprocess.call(docker_compose_command, shell=True, cwd=os.path.join(backplane_active_context_dir,service,backplane_environment))
      
      typer.secho(f"Successfully started {service} in {backplane_active_context_dir}", err=False, fg=typer.colors.GREEN)
    except Exception as e:
      typer.secho(f"Failed to start {service} in {backplane_active_context_dir}: {e}", err=True, fg=typer.colors.RED)
      raise typer.Exit(code=1)


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
  backplane_verbosity = verbosity
  typer.secho(f"Verbosity: {verbosity}", err=False, fg=typer.colors.GREEN)


if __name__ == "__main__":
    app()
