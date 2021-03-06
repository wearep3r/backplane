#!/usr/bin/env python3

import typer
import os
from shutil import which
import sys
from typing import Optional, List
from pathlib import Path
from read_version import read_version
from backplane import utils
from backplane.config import Config
from backplane.app import App
from backplane.service import Service
from backplane.errors import ConfigNotFound, CannotStartService
from requests import get
import subprocess
from git.repo.base import Repo

# Linux
# ('Linux', '5.4.0-52-generic', '#57-Ubuntu SMP Thu Oct 15 10:57:00 UTC 2020')
# 5.4.0-52-generic

# Darwin
# ('Darwin', '19.6.0', 'Darwin Kernel Version 19.6.0: Thu Jun 18 20:49:00 PDT 2020; root:xnu-6153.141.1~1/RELEASE_X86_64')
# 19.6.0
# print(platform.system())
# print(platform.system_alias(platform.system(), platform.release(), platform.version()))
# print(platform.release())
# print(platform.platform())

app = typer.Typer(help="backplane CLI")

# Set config
conf = Config()


@app.command()
def init(
    reinstall: bool = typer.Option(
        False, "--reinstall", "-r", help="Uninstall backplane first"
    ),
    domain: str = typer.Option(
        None,
        "--domain",
        "-d",
        help="The domain your backplane runs on",
    ),
    mail: str = typer.Option(
        None,
        "--mail",
        "-m",
        help="The mail address used for LetsEncrypt",
    ),
    no_docker: bool = typer.Option(
        False, "--no-docker", help="Don't create backplane network"
    ),
    user: str = typer.Option(
        conf.user,
        "--user",
        "-u",
        help="User for authentication",
    ),
    password: str = typer.Option(
        conf.password,
        "--password",
        "-p",
        help="Password for authentication",
    ),
    https: bool = typer.Option(False, "--https", "-h", help="Enable https support"),
    ssh_public_key: str = typer.Option(
        None, "--ssh-public-key", help="public ssh key to add to the runner"
    ),
    ssh_public_key_file: str = typer.Option(
        None,
        "--ssh-public-key-file",
        help="public ssh key file to add to the runner",
    ),
):
    """
    Initialize backplane
    """

    if reinstall:
        rm(force=True)

    # Create config dir
    utils.createDir(conf.config_dir)

    # Create contexts dir
    utils.createDir(conf.contexts_dir)

    # Create default context dir
    utils.createDir(conf.default_context_dir)

    # Create apps dir
    utils.createDir(conf.app_dir)

    # Create Docker network
    if not no_docker:
        utils.createNetwork("backplane")

    # Prepare custom config
    backplane_config = {}
    backplane_config_dir = conf.config_path

    if https:
        backplane_config["https"] = True

    # A custom domain has been set
    if domain:
        backplane_config["domain"] = domain
    else:
        backplane_config[
            "domain"
        ] = f"{get('https://api.ipify.org').text.replace('.','-')}.ns0.co"

    if user:
        backplane_config["user"] = user

    if password:
        backplane_config["password"] = password

        # Generate password hash
        try:
            password_hash = subprocess.run(
                ["htpasswd", "-nbB", user, password], stdout=subprocess.PIPE
            )
            backplane_config["password_hash"] = (
                password_hash.stdout.rstrip().decode().split(":")[1]
            )
        except OSError as e:
            typer.secho(
                f"Cannot generate password hash: {e} (try 'apt install apache2-utils' to fix this",
                err=True,
                fg=typer.colors.RED,
            )
            sys.exit(1)

    # A custom mail has been set
    if mail:
        backplane_config["mail"] = mail

    if ssh_public_key:
        backplane_config["ssh_public_key"] = ssh_public_key

    if ssh_public_key_file:
        backplane_config["ssh_public_key_file"] = ssh_public_key_file

    if backplane_config:
        utils.writeConfig(backplane_config_dir, backplane_config)
        if conf.verbose > 0:
            typer.secho(
                f"Saving new config to {backplane_config_dir}",
                err=False,
                fg=typer.colors.BRIGHT_BLACK,
            )

    typer.secho(
        "Installation successful. Use 'backplane up' to get going.",
        err=False,
        fg=typer.colors.GREEN,
    )


@app.command()
def rm(
    force: bool = typer.Option(False, "--force", "-f", help="Remove service volumes"),
):
    """
    Remove backplane. Removes all services.
    """

    # Stop services
    down(service=None, prune=force)

    # Remove config dir
    utils.rmDir(conf.config_dir)

    # Remove network
    utils.rmNetwork("backplane")

    typer.secho("Successfully uninstalled backplane", err=False, fg=typer.colors.GREEN)


@app.command()
def up(
    service: str = typer.Argument(
        None,
    ),
    restart: bool = typer.Option(False, "--restart", "-r", help="Restart services"),
):
    """
    Start backplane. Starts all services.
    """

    backplane_service = service

    if not backplane_service:
        services = conf.default_services
    else:
        services = [service]

    for service in services:
        s = Service(name=service, config=conf)
        if conf.verbose > 0:
            typer.secho(
                f"up: starting {s.name}",
                err=False,
                fg=typer.colors.BRIGHT_BLACK,
            )

        try:
            if restart:
                s.stop()
                s.remove()

            s.start()
            s.echo()
        except CannotStartService as e:
            typer.secho(
                f"Unable to start service {service}: {e}",
                err=True,
                fg=typer.colors.RED,
            )
            sys.exit(1)
        except Exception as e:
            typer.secho(
                f"Unable to start service {service}: {e}",
                err=True,
                fg=typer.colors.RED,
            )
            sys.exit(1)


@app.command()
def restart(
    service: str = typer.Argument(
        None,
        help="Service to restart",
    ),
):
    """
    Restart service.
    """
    up(service=service, restart=True)


@app.command()
def down(
    service: str = typer.Argument(None),
    prune: bool = typer.Option(False, "--prune", "-p", help="Remove volumes"),
):
    """
    Stop backplane. Stops all services.
    """

    if conf.verbose > 0:
        typer.secho(
            f"Shutting down {service}",
            err=False,
            fg=typer.colors.BRIGHT_BLACK,
        )

    backplane_service = service

    if not backplane_service:
        services = conf.default_services
    else:
        services = [backplane_service]

    for service in services:
        s = Service(name=service, config=conf)

        try:
            s.stop()

            if prune:
                s.remove(prune=True)
            else:
                s.remove()

            s.echo()
        except Exception as e:
            typer.secho(
                f"Unable to stop service {service}: {e}",
                err=True,
                fg=typer.colors.RED,
            )
            sys.exit(1)


@app.command()
def install(
    registry_app: str = typer.Argument(None),
    name: str = typer.Option(None, "--name", "-n"),
    source: str = typer.Option(None, "--from", "-f"),
    destination: Path = typer.Option(None, "--to", "-t"),
    compose_file: str = typer.Option("docker-compose.yml", "--compose-file", "-c"),
):
    """
    Install an app into backplane.
    """

    if conf.verbose > 0:
        typer.secho(
            f"Installing {name} from {destination}",
            err=False,
            fg=typer.colors.BRIGHT_BLACK,
        )
    app_name = name if name else os.path.basename(os.getcwd())
    app_source = source if source else os.getcwd()
    app_destination = destination if destination else os.getcwd()

    # Check if an app has been named to be taken from the app registry
    if registry_app:
        app_name = name if name else registry_app
        app_destination = os.path.join(conf.app_dir, app_name)

        try:
            backplane_app = App(
                compose_file=compose_file,
                config=conf,
                destination=app_destination,
                name=app_name,
                registry_app=registry_app,
                source="registry",
            )
            backplane_app.install()
        except Exception as e:
            typer.secho(
                f"Failed to install {name} from {path}: {e}",
                err=True,
                fg=typer.colors.RED,
            )
    elif source and not destination:
        app_name = utils.get_repo_name_from_url(source)
        app_destination = os.path.join(conf.app_dir, app_name)

        # Specified a source but no destination
        # set destination to app_dir/app_name
        try:
            backplane_app = App(
                compose_file=compose_file,
                config=conf,
                destination=app_destination,
                name=app_name,
                registry_app=registry_app,
                source=app_source,
            )
            backplane_app.install()
        except Exception as e:
            typer.secho(
                f"Failed to install {name} from {destination}: {e}",
                err=True,
                fg=typer.colors.RED,
            )
    else:
        try:
            # Set name if given or default to app name
            backplane_app = App(
                compose_file=compose_file,
                config=conf,
                destination=app_destination,
                name=app_name,
                registry_app=registry_app,
                source=app_source,
            )
            backplane_app.install()
        except Exception as e:
            typer.secho(
                f"Failed to install {name} from {destination}: {e}",
                err=True,
                fg=typer.colors.RED,
            )


@app.command()
def config():
    if conf.verbose > 0:
        typer.secho(
            f"Loaded user config from {conf.active_context_dir}/backplane.yml",
            err=False,
            fg=typer.colors.BRIGHT_BLACK,
        )

    typer.secho(
        conf.dump(),
        err=False,
        fg=typer.colors.BRIGHT_GREEN,
    )


@app.command()
def status(
    service: str = typer.Argument(None),
):
    """
    backplane status.
    """
    if not service:
        services = conf.default_services
    else:
        services = [service]

    for service in services:
        s = Service(service, conf)
        s.echo()


def version_callback(value: bool):
    if value:
        version = read_version(".", "__init__.py")
        typer.echo(f"{version}")
        raise typer.Exit()


def checkPrerequisites(ctx):
    # Check for Docker
    # if not which("docker"):
    #     if ctx.invoked_subcommand == "init":
    #         pass
    #     else:
    #         typer.secho("Docker not installed", err=True, fg=typer.colors.RED)
    #         raise typer.Abort()

    if not os.path.exists(conf.config_dir):
        if ctx.invoked_subcommand == "init":
            pass
        else:
            typer.secho(
                "config directory missing. Run 'backplane init' first.",
                err=True,
                fg=typer.colors.RED,
            )
            sys.exit(1)

    if not os.path.exists(conf.active_context_dir):
        if ctx.invoked_subcommand == "init":
            pass
        else:
            typer.secho(
                "active context directory missing. Run 'backplane init' first.",
                err=True,
                fg=typer.colors.RED,
            )
            sys.exit(1)


@app.command()
def context(context: Optional[str] = typer.Argument("default")):
    _active_context = os.path.join(conf.config_dir, ".active_context")
    # Load ~/.backplane/.active_context
    active_context = context
    if not os.path.exists(_active_context):
        try:
            with open(os.path.join(_active_context), "w+") as writer:
                writer.write(context)
                writer.truncate()
                active_context = context
        except Exception as e:
            typer.secho(
                f"Can't create context file: {e}",
                err=True,
                fg=typer.colors.RED,
            )
            sys.exit(1)
            typer.echo(active_context)
        return active_context
    else:
        try:
            with open(os.path.join(conf.config_dir, ".active_context"), "r") as reader:
                active_context = reader.read()
        except Exception as e:
            typer.secho(
                f"Can't load active context: {e}",
                err=True,
                fg=typer.colors.RED,
            )
            sys.exit(1)

    if context != active_context:
        typer.echo("Context changed")
        try:
            with open(os.path.join(conf.config_dir, ".active_context"), "r+") as writer:
                writer.write(context)
                writer.truncate()
                active_context = context
        except Exception as e:
            typer.secho(
                f"Can't save active context: {e}",
                err=True,
                fg=typer.colors.RED,
            )
            sys.exit(1)
    typer.echo(active_context)
    return active_context


@app.callback()
def callback(
    ctx: typer.Context,
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose"),
    version: Optional[bool] = typer.Option(
        None, "--version", callback=version_callback, is_eager=True
    ),
    config_path: Path = typer.Option(
        conf.config_path,
        "--config-file",
        "-c",
        help="Path to backplane.yml",
    ),
):

    # Update config
    try:
        if config_path:
            new_config = Config(config_path)
        else:
            new_config = Config()
    except ConfigNotFound as e:
        typer.secho(
            f"Failed to load config: {e}",
            err=True,
            fg=typer.colors.RED,
        )
        sys.exit(1)
    config = new_config

    # Check pre-reqs
    checkPrerequisites(ctx)

    conf.verbose = verbose

    # LOAD CONFIG HERE
    # backplane_config = anyconfig.load(config_file)

    version = read_version(".", "__init__.py")
    if conf.verbose > 0:
        typer.secho(f"Version: {version}", err=False, fg=typer.colors.BRIGHT_BLACK)
        typer.secho(
            f"Context: {conf.active_context}",
            err=False,
            fg=typer.colors.BRIGHT_BLACK,
        )
        typer.secho(
            f"Context directory: {conf.active_context_dir}",
            err=False,
            fg=typer.colors.BRIGHT_BLACK,
        )
        typer.secho(
            f"Config file: {conf.config_path}",
            err=False,
            fg=typer.colors.BRIGHT_BLACK,
        )


if __name__ == "__main__":
    app()
