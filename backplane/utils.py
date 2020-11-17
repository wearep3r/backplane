import subprocess
import os
import sys
import requests
import platform
import typer
import docker
import anyconfig
import json


def rmNetwork(network: str):
    # Remove network
    try:
        docker_client = docker.from_env()
        docker_networks = docker_client.networks.list(names=network)
        for network in docker_networks:
            if network.name == network:
                if "provider" in network.attrs["Labels"].keys():
                    if network.attrs["Labels"]["provider"] == network:
                        network.remove()
        return True
    except Exception as e:
        typer.secho(
            f"Failed to remove backplane Docker network: {e}",
            err=True,
            fg=typer.colors.RED,
        )
        sys.exit(1)


def createNetwork(network: str):
    # Make sure Docker network "backplane" exists
    backplane_network_exists = False

    try:
        docker_client = docker.from_env()
        docker_networks = docker_client.networks.list(names=network)

        for docker_network in docker_networks:
            if docker_network.name == network:
                if "provider" in docker_network.attrs["Labels"].keys():
                    if docker_network.attrs["Labels"]["provider"] == "backplane":
                        backplane_network_exists = True
    except Exception as e:
        typer.secho(
            f"Failed to lookup backplane Docker network: {e}",
            err=True,
            fg=typer.colors.RED,
        )
        sys.exit(1)

    if not backplane_network_exists:
        try:
            docker_client = docker.from_env()
            backplane_network = docker_client.networks.create(
                name=network,
                check_duplicate=True,
                labels={"provider": network},
                attachable=True,
            )
            return backplane_network
        except Exception as e:
            error = True
            typer.secho(
                f"Failed to create backplane Docker network: {e}",
                err=True,
                fg=typer.colors.RED,
            )
            sys.exit(1)


def readConfig(config_path: str, backplane):
    try:
        backplane_config = backplane
        if os.path.exists(config_path):
            custom_config = anyconfig.load([config_path])
            backplane_rc = backplane
            anyconfig.merge(backplane_rc, custom_config)
            backplane_config = backplane_rc

        return backplane_config
    except OSError as e:
        typer.secho(
            f"Couldn't read backplane config at {config_path}: {e}",
            err=True,
            fg=typer.colors.RED,
        )
        sys.exit(1)


def writeConfig(config_path: str, config):
    try:
        backplane_config = anyconfig.loads(json.dumps(config), ac_parser="json")
        # anyconfig.merge(backplane_config, config)
        # if os.path.exists(config_path):

        # Open ~/.backplane/contexts/default/backplane.yml
        # Save config as yml
        with open(config_path, "w+") as writer:
            writer.write(anyconfig.dumps(backplane_config, ac_parser="yaml"))

        return backplane_config
    except OSError as e:
        typer.secho(
            f"Couldn't write backplane config at {config_path}: {e}",
            err=True,
            fg=typer.colors.RED,
        )
        sys.exit(1)


def createDir(directory: str):
    if not os.path.exists(directory):
        try:
            os.mkdir(directory)
        except OSError as e:
            error = True
            typer.secho(
                f"Couldn't create directory {directory}: {e}",
                err=True,
                fg=typer.colors.RED,
            )
            sys.exit(1)


def rmDir(directory: str):
    try:
        subprocess.run(
            [
                "rm",
                "-rf",
            ]
        )
        return True
    except OSError as e:
        typer.secho(
            f"config directory {directory} could not be removed: {e}",
            err=True,
            fg=typer.colors.RED,
        )


def getDynamicDomain(environment: str = "sss"):
    domain = backplane["domain"]
    if environment == "production":
        try:
            f = requests.request("GET", "https://ifconfig.me")
            ip = f.text.replace(".", "-")

            domain = f"{ip}.nip.io"
        except Exception as e:
            typer.secho(
                f"Couldn't determine dynamic domain: {e}",
                err=True,
                fg=typer.colors.RED,
            )
            raise typer.Exit(code=1)

    return domain


def printStatus(container, service, backplane):
    message_name = typer.style(f"{container.name.strip('/')}: ", bold=True)

    if container.status == "running":
        message_prefix = typer.style(" ∟ ", fg=typer.colors.GREEN)
        message_status = typer.style(
            f"{container.status}", fg=typer.colors.GREEN, bold=True
        )
    else:
        message_prefix = typer.style(" ∟ ", fg=typer.colors.RED)
        message_status = typer.style(
            f"{container.status}", fg=typer.colors.WHITE, bg=typer.colors.RED
        )

    # Assemble output
    output = [message_prefix, message_name, message_status]

    # Add service URL if container is running
    if container.status == "running":
        message_url = [
            typer.style(" at "),
            typer.style(
                f"http://{backplane['services'][service]['url']}",
                fg=typer.colors.BLUE,
            ),
        ]
        output = output + message_url

    typer.echo("".join(output))