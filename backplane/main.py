#!/usr/bin/env python3

import typer
import os
import subprocess
import yaml
import json
import re
import anyconfig
from dotenv import load_dotenv
import docker
from shutil import which
import sys
import platform
from typing import Optional
from packaging import version
import requests

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

backplane_echo_indent = "  "
backplane_echo_prefix = "- "

backplane = {}


def getDynamicDomain():
    f = requests.request("GET", "https://ifconfig.me")
    ip = f.text.replace(".", "-")

    domain = f"{ip}.nip.io"
    return domain


@app.command()
def install(
    domain: str = typer.Option(
        getDynamicDomain(), "--domain", "-d", help="The domain your backplane runs on"
    ),
    mail: str = typer.Option(
        "",
        "--mail",
        "-m",
        help="The mail address used for LetsEncrypt",
    ),
    environment: str = typer.Option(
        "development", "--environment", "-e", help="backplane environment"
    ),
    ssh_public_key: str = typer.Option(
        "", "--ssh-public-key", help="public ssh key to add to the runner"
    ),
    ssh_public_key_file: str = typer.Option(
        f"{os.getenv('HOME')}/.ssh/id_rsa.pub",
        "--ssh-public-key-file",
        help="public ssh key file to add to the runner",
    ),
):
    error = False
    ssh_defaults = 'no-port-forwarding,no-X11-forwarding,no-agent-forwarding,no-pty,command="/usr/local/bin/backplane-ssh"'

    # backplane['config_dir']
    if not os.path.exists(backplane["config_dir"]):
        if backplane["verbosity"] > 0:
            typer.secho(
                f"config directory {backplane['config_dir']} does not exist",
                err=True,
                fg=typer.colors.RED,
            )
        try:
            os.mkdir(backplane["config_dir"])
        except OSError as e:
            error = True
            typer.secho(
                f"config directory {backplane['config_dir']} could not be created: {e}",
                err=True,
                fg=typer.colors.RED,
            )
            raise typer.Exit(code=1)
        else:
            if backplane["verbosity"] > 0:
                typer.secho(
                    f"config directory {backplane['config_dir']} created",
                    err=False,
                    fg=typer.colors.GREEN,
                )

    else:
        if backplane["verbosity"] > 0:
            typer.secho(
                f"config directory {backplane['config_dir']} exists",
                err=False,
                fg=typer.colors.GREEN,
            )

    # backplane['contexts_dir']
    if not os.path.exists(backplane["contexts_dir"]):
        if backplane["verbosity"] > 0:
            typer.secho(
                f"contexts directory {backplane['contexts_dir']} does not exist",
                err=True,
                fg=typer.colors.RED,
            )
        try:
            os.mkdir(backplane["contexts_dir"])
        except OSError as e:
            error = True
            typer.secho(
                f"contexts directory {backplane['contexts_dir']} could not be created: {e}",
                err=True,
                fg=typer.colors.RED,
            )
            raise typer.Exit(code=1)
        else:
            if backplane["verbosity"] > 0:
                typer.secho(
                    f"contexts directory {backplane['contexts_dir']} created",
                    err=False,
                    fg=typer.colors.GREEN,
                )

    else:
        if backplane["verbosity"] > 0:
            typer.secho(
                f"contexts directory {backplane['contexts_dir']} exists",
                err=False,
                fg=typer.colors.GREEN,
            )

    # backplane['default_context_dir']
    if not os.path.exists(backplane["default_context_dir"]):
        if backplane["verbosity"] > 0:
            typer.secho(
                f"default context directory {backplane['default_context_dir']} does not exist",
                err=True,
                fg=typer.colors.RED,
            )

        try:
            backplane_repo = os.getenv(
                "BACKPLANE_REPOSITORY", "https://gitlab.com/p3r.one/backplane.git/"
            )
            clone_command = (
                f"git clone {backplane_repo} {backplane['default_context_dir']}"
            )
            clone = subprocess.call(clone_command, shell=True)

            if backplane["verbosity"] > 0:
                typer.secho(
                    f"Successfully cloned {backplane_repo} to {backplane['default_context_dir']}",
                    err=False,
                    fg=typer.colors.GREEN,
                )

        except Exception as e:
            typer.secho(
                f"Failed to clone backplane repository from {backplane_repo} to {backplane['default_context_dir']}: {e}",
                err=True,
                fg=typer.colors.RED,
            )

            if backplane["verbosity"] > 0:
                typer.secho(f"{clone_command}", err=False, fg=typer.colors.BRIGHT_BLACK)

            error = True
            raise typer.Exit(code=1)
    else:
        if backplane["verbosity"] > 0:
            typer.secho(
                f"default context directory {backplane['default_context_dir']} exists",
                err=False,
                fg=typer.colors.GREEN,
            )

    # make sure .env file exists
    if not os.path.exists(backplane["default_context_dir"] + "/.env"):
        if backplane["verbosity"] > 0:
            typer.secho("default config does not exist", err=True, fg=typer.colors.RED)

        if environment == "development":
            domain = "127-0-0-1.nip.io"
            # try:
            #     subprocess.run(
            #         ["cp", ".env.example", ".env"],
            #         cwd=backplane["default_context_dir"],
            #     )
            #     if backplane["verbosity"] > 0:
            #         typer.secho(
            #             "Successfully created default config",
            #             err=False,
            #             fg=typer.colors.GREEN,
            #         )

            # except Exception as e:
            #     error = True
            #     typer.secho(
            #         f"Failed to create default config: {e}",
            #         err=True,
            #         fg=typer.colors.RED,
            #     )
            #     raise typer.Exit(code=1)
        try:
            # Generate special public format
            public_key = ""
            if ssh_public_key != "":
                public_key = f"{ssh_defaults} {ssh_public_key}"
            else:
                with open(ssh_public_key_file, "r") as reader:
                    pubkey = reader.read().rstrip()
                    public_key = f"{ssh_defaults} {pubkey}"

            env_file = [
                f"BACKPLANE_DOMAIN={domain}",
                f"BACKPLANE_ENVIRONMENT={environment}",
                f"BACKPLANE_MAIL={mail}",
                f"BACKPLANE_RUNNER_PUBLIC_KEY='{public_key}'",
                "",
            ]
            with open(f"{backplane['default_context_dir']}/.env", "w") as writer:
                writer.write("\n".join(env_file))

        except Exception as e:
            error = True
            typer.secho(
                f"Failed to create default config: {e}",
                err=True,
                fg=typer.colors.RED,
            )
            raise typer.Exit(code=1)
    else:
        if backplane["verbosity"] > 0:
            typer.secho("default config exists", err=False, fg=typer.colors.GREEN)

    # Update BACKPLANE_DOMAIN in .env file from "--domain"

    # Make sure Docker network "backplane" exists
    backplane_network_exists = False
    docker_client = docker.from_env()
    docker_networks = docker_client.networks.list(names="backplane")

    for network in docker_networks:
        if network.name == "backplane":
            if "provider" in network.attrs["Labels"].keys():
                if network.attrs["Labels"]["provider"] == "backplane":
                    backplane_network_exists = True

    if not backplane_network_exists:
        try:
            backplane_network = docker_client.networks.create(
                name="backplane",
                check_duplicate=True,
                labels={"provider": "backplane"},
                attachable=True,
            )
            if backplane["verbosity"] > 0:
                typer.secho(
                    f"Successfully created backplane Docker network",
                    err=False,
                    fg=typer.colors.GREEN,
                )

        except Exception as e:
            error = True
            typer.secho(
                f"Failed to create backplane Docker network: {e}",
                err=True,
                fg=typer.colors.RED,
            )
            raise typer.Exit(code=1)
    else:
        if backplane["verbosity"] > 0:
            typer.secho(
                "backplane Docker network exists", err=False, fg=typer.colors.GREEN
            )

    if not error:
        typer.secho(
            f"Installation successful. Use 'backplane start' to get going.",
            err=False,
            fg=typer.colors.GREEN,
        )
    else:
        typer.secho(
            f"Installation failed. Use 'backplane -v 1 install' for verbose output.",
            err=False,
            fg=typer.colors.GREEN,
        )


@app.command()
def uninstall(
    force: bool = typer.Option(False, "--force", "-f", help="Remove volumes"),
):
    # Stop services
    stop(remove=force, services="traefik,portainer")

    # Remove backplane
    try:
        subprocess.run(["rm", "-rf", backplane["config_dir"]])
    except OSError as e:
        typer.secho(
            f"config directory {backplane['config_dir']} could not be removed: {e}",
            err=True,
            fg=typer.colors.RED,
        )

    # Remove network
    docker_client = docker.from_env()
    docker_networks = docker_client.networks.list(names="backplane")
    for network in docker_networks:
        if network.name == "backplane":
            if "provider" in network.attrs["Labels"].keys():
                if network.attrs["Labels"]["provider"] == "backplane":
                    network.remove()

    typer.secho("Successfully uninstalled backplane", err=False, fg=typer.colors.GREEN)


@app.command()
def update():
    typer.secho(
        f"Updating backplane in {backplane['default_context_dir']} ...",
        err=False,
        fg=typer.colors.GREEN,
    )
    try:
        backplane_repo = os.getenv(
            "BACKPLANE_REPOSITORY", "git@gitlab.com:p3r.one/backplane.git"
        )
        pull_command = f"git pull origin master"
        pull = subprocess.call(
            pull_command, shell=True, cwd=backplane["default_context_dir"]
        )

        typer.secho(f"Successfully updated backplane", err=False, fg=typer.colors.GREEN)
    except Exception as e:
        typer.secho(f"Failed to update backplane: {e}", err=True, fg=typer.colors.RED)

        if backplane["verbosity"] > 0:
            typer.secho(f"{pull_command}", err=False, fg=typer.colors.BRIGHT_BLACK)

        raise typer.Exit(code=1)


def runCommand(
    compose_command: str,
    project_dir: str,
):

    try:
        # Load .env file
        from pathlib import Path  # Python 3.6+ only

        env_path = Path(backplane["default_context_dir"]) / ".env"
        load_dotenv(dotenv_path=env_path)

        result = subprocess.run(
            compose_command, shell=True, cwd=project_dir, capture_output=True
        )
        return result
    except Exception as e:
        typer.secho(
            f"Failed to execute command `{compose_command}` in {project_dir}: {e}",
            err=True,
            fg=typer.colors.RED,
        )
        raise typer.Exit(code=1)


def getContainerIDs(service: str):
    docker_compose_command = (
        f"docker-compose -f docker-compose.yml -p backplane-{service} ps -q"
    )
    project_dir = os.path.join(
        backplane["active_context_dir"], service, backplane["environment"]
    )

    if backplane["verbosity"] > 0:
        typer.secho(f"{docker_compose_command}", err=False, fg=typer.colors.BRIGHT_BLACK)

    container_ids = runCommand(docker_compose_command, project_dir)

    if container_ids.returncode != 0:
        typer.secho(
            f"Failed to get status for service {service} in {backplane['active_context_dir']}: {container_ids.stdout}",
            err=True,
            fg=typer.colors.RED,
        )
        raise typer.Exit(code=container_ids)

    return container_ids.stdout.decode().split("\n")


@app.command()
def start(
    services: str = typer.Option(
        "traefik,portainer", "--services", "-s", help="Services to start"
    ),
):
    backplane_services = services.split(",")

    for service in backplane_services:
        docker_compose_command = f"docker-compose -f docker-compose.yml -p backplane-{service} up -d --remove-orphans"
        project_dir = os.path.join(
            backplane["active_context_dir"], service, backplane["environment"]
        )

        if backplane["verbosity"] > 0:
            typer.secho(
                f"{docker_compose_command}", err=False, fg=typer.colors.BRIGHT_BLACK
            )

        result = runCommand(docker_compose_command, project_dir)
        if result.returncode != 0:
            typer.secho(
                f"Failed to start {service} in {backplane['active_context_dir']}: {result.stderr}",
                err=True,
                fg=typer.colors.RED,
            )
            raise typer.Exit(code=result)
        else:
            if backplane["verbosity"] > 0:
                typer.secho(
                    f"Successfully started {service} in {backplane['active_context_dir']}",
                    err=False,
                    fg=typer.colors.GREEN,
                )

    status(services)


@app.command()
def restart(
    services: str = typer.Option(
        "traefik,portainer", "--services", "-s", help="Services to restart"
    ),
):
    backplane_services = services.split(",")

    for service in backplane_services:
        docker_compose_command = f"docker-compose -f docker-compose.yml -p backplane-{service} restart {service}"
        project_dir = os.path.join(
            backplane["active_context_dir"], service, backplane["environment"]
        )

        if backplane["verbosity"] > 0:
            typer.secho(
                f"{docker_compose_command}", err=False, fg=typer.colors.BRIGHT_BLACK
            )

        result = runCommand(docker_compose_command, project_dir)
        if result.returncode != 0:
            typer.secho(
                f"Failed to restart {service} in {backplane['active_context_dir']}: {result.stdout}",
                err=True,
                fg=typer.colors.RED,
            )
            raise typer.Exit(code=result)
        else:
            if backplane["verbosity"] > 0:
                typer.secho(
                    f"Successfully restarted {service} in {backplane['active_context_dir']}",
                    err=False,
                    fg=typer.colors.GREEN,
                )

    status(services)


@app.command()
def stop(
    services: str = typer.Option(
        "traefik,portainer", "--services", "-s", help="Services to stop"
    ),
    remove: bool = typer.Option(False, "--remove", "-r", help="Remove all data"),
):
    backplane_services = services.split(",")

    for service in backplane_services:
        if remove:
            docker_compose_command = f"docker-compose -f docker-compose.yml -p backplane-{service} down -v --rmi all --remove-orphans"
        else:
            docker_compose_command = (
                f"docker-compose -f docker-compose.yml -p backplane-{service} stop"
            )
        project_dir = os.path.join(
            backplane["active_context_dir"], service, backplane["environment"]
        )

        if backplane["verbosity"] > 0:
            typer.secho(
                f"{docker_compose_command}", err=False, fg=typer.colors.BRIGHT_BLACK
            )

        result = runCommand(docker_compose_command, project_dir)
        if result.returncode != 0:
            typer.secho(
                f"Failed to stop {service} in {backplane['active_context_dir']}: {result.stdout}",
                err=True,
                fg=typer.colors.RED,
            )
            raise typer.Exit(code=result)
        else:
            if backplane["verbosity"] > 0:
                typer.secho(
                    f"Successfully stopped {service} in {backplane['active_context_dir']}",
                    err=False,
                    fg=typer.colors.GREEN,
                )

    status(services)


@app.command()
def status(
    services: str = typer.Option(
        "traefik,portainer", "--services", "-s", help="Services to get status for"
    ),
):
    backplane_services = services.split(",")

    overall_status = []

    for service in backplane_services:
        service_status = []

        for container_id in getContainerIDs(service):
            if container_id != "":
                docker_client = docker.from_env()
                container = docker_client.containers.get(container_id)

                attrs = container.attrs

                status = {
                    "id": attrs["Id"],
                    "image": attrs["Config"]["Image"],
                    "name": attrs["Name"],
                    "restarts": attrs["RestartCount"],
                    "status": attrs["State"]["Status"],
                }

                # Get Ports
                ports = []
                for port in attrs["Config"]["ExposedPorts"].keys():
                    ports.append(port)
                status["ports"] = ports

                # Get URLs
                status["urls"] = []
                for label in attrs["Config"]["Labels"].keys():
                    if ".rule" in label:
                        regex = r"Host\(`([a-zA-Z0-9.].*)*`\)"
                        urls_matched = re.findall(regex, attrs["Config"]["Labels"][label])

                        for url in urls_matched:
                            status["urls"].append(url)
                        status["urls"] = list(set(status["urls"]))

                # print(json_data)
                # json.dumps(container_status.stdout.decode())
                service_status.append(status)

        # Output Status information
        typer.echo(f"{backplane_echo_prefix}Service: {service}")
        typer.echo(f"{backplane_echo_indent}Environment: {backplane['environment']}")
        typer.echo(f"{backplane_echo_indent}Context: {backplane['active_context']}")
        typer.echo(f"{backplane_echo_indent}Containers:")

        for container in service_status:
            # Container status
            local_indent = backplane_echo_indent * 2
            message_status = f"{local_indent}{backplane_echo_prefix}Status: "

            if container["status"] == "running":
                ending = typer.style(
                    f"{container['status']}", fg=typer.colors.GREEN, bold=True
                )
            else:
                ending = typer.style(
                    f"{container['status']}", fg=typer.colors.WHITE, bg=typer.colors.RED
                )
            message_status = message_status + ending
            typer.echo(message_status)

            local_indent = backplane_echo_indent * 3
            typer.echo(f"{local_indent}Name: {container['name'].strip('/')}")
            typer.echo(f"{local_indent}ID: {container['id']}")
            typer.echo(f"{local_indent}Image: {container['image']}")
            typer.echo(f"{local_indent}Restarts: {container['restarts']}")
            typer.echo(f"{local_indent}URLs: ")

            local_indent = backplane_echo_indent * 4
            for url in container["urls"]:
                typer.echo(f"{local_indent}{backplane_echo_prefix}http://{url}")

        overall_status.append(service_status)

    return overall_status


@app.command()
def logs(
    services: str = typer.Option(
        "traefik,portainer", "--services", "-s", help="Services to get logs for"
    )
):
    backplane_services = services.split(",")

    for service in backplane_services:
        for container_id in getContainerIDs(service):
            if container_id != "":
                docker_client = docker.from_env()
                container = docker_client.containers.get(container_id)

                if backplane["verbosity"] > 0:
                    typer.secho(
                        f"{container_id}", err=False, fg=typer.colors.BRIGHT_BLACK
                    )

                print(container.logs(tail=200).decode())


def version_callback(value: bool):
    if value:
        typer.echo(f"backplane CLI: {__version__}")
        raise typer.Exit()


def checkPrerequisites(ctx):
    # Check for Docker
    if not which("docker"):
        typer.secho("Docker not installed", err=True, fg=typer.colors.RED)
        sys.exit(1)

    if not which("docker-compose"):
        typer.secho("docker-compose not installed", err=True, fg=typer.colors.RED)
        sys.exit(1)
    else:
        docker_compose_version = subprocess.run(
            ["docker-compose", "-v"], capture_output=True
        )
        doco_version = docker_compose_version.stdout.decode().split(" ")[2].strip(",")

        if version.parse(doco_version) < version.parse("1.27.4"):
            typer.secho(
                f"docker-compose version {doco_version} does not match minimum required version 1.27.4",
                err=True,
                fg=typer.colors.RED,
            )
            sys.exit(1)

    if not which("git"):
        typer.secho("git not installed", err=True, fg=typer.colors.RED)
        sys.exit(1)

    if not os.path.exists(backplane["config_dir"]):
        if ctx.invoked_subcommand == "install":
            pass
        else:
            typer.secho(
                "config directory missing. Run 'backplane install' first.",
                err=True,
                fg=typer.colors.RED,
            )
            sys.exit(1)

    if not os.path.exists(backplane["active_context_dir"]):
        if ctx.invoked_subcommand == "install":
            pass
        else:
            typer.secho(
                "active context directory missing. Run 'backplane install' first.",
                err=True,
                fg=typer.colors.RED,
            )
            sys.exit(1)


@app.callback()
def callback(
    ctx: typer.Context,
    verbosity: bool = typer.Option(False, "--verbose", "-v", help="Verbose"),
    version: Optional[bool] = typer.Option(
        None, "--version", callback=version_callback, is_eager=True
    ),
):

    backplane["config_dir"] = os.getenv(
        "BACKPLANE_CONIG_DIR", os.path.join(os.getenv("HOME", "~"), ".backplane")
    )
    backplane["active_context"] = os.getenv("backplane['active_context']", "default")
    backplane["contexts_dir"] = os.getenv(
        "BACKPLANE_CONTEXTS_DIR", os.path.join(backplane["config_dir"], "contexts")
    )
    backplane["default_context_dir"] = os.getenv(
        "BACKPLANE_DEFAULT_CONTEXT_DIR",
        os.path.join(backplane["contexts_dir"], backplane["active_context"]),
    )
    backplane["active_context_dir"] = backplane["default_context_dir"]

    # Load .env from active context
    load_dotenv(dotenv_path=f"{backplane['active_context_dir']}/.env")

    backplane["verbosity"] = verbosity

    backplane["environment"] = os.getenv("BACKPLANE_ENVIRONMENT", "development")

    checkPrerequisites(ctx)

    if backplane["verbosity"] > 0:
        typer.secho(f"backplane v1.2.0", err=False, fg=typer.colors.BRIGHT_BLACK)
        typer.secho(
            f"Environment: {backplane['environment']}",
            err=False,
            fg=typer.colors.BRIGHT_BLACK,
        )
        typer.secho(
            f"Context: {backplane['active_context']}",
            err=False,
            fg=typer.colors.BRIGHT_BLACK,
        )
        typer.secho(
            f"Context Directory: {backplane['active_context_dir']}",
            err=False,
            fg=typer.colors.BRIGHT_BLACK,
        )


if __name__ == "__main__":
    app()
