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
import time

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

backplane = {
    "config_dir": os.getenv(
        "BACKPLANE_CONIG_DIR", os.path.join(os.getenv("HOME", "~"), ".backplane")
    ),
    "default_context": "default",
    "active_context": "default",
    "environment": "development",
    "domain": "127-0-0-1.nip.io",
    "mail": "",
    "default_services": "traefik,portainer,runner",
    "verbose": False,
}

backplane["services"] = {
    "traefik": {
        "domain": f"traefik.{backplane['domain']}",
    },
    "portainer": {"domain": f"portainer.{backplane['domain']}"},
}

# Attributes
backplane["services"]["traefik"]["attrs"] = {
    "image": "traefik:v2.3",
    "command": [
        "--global.checkNewVersion=false",
        "--global.sendAnonymousUsage=false",
        "--entryPoints.http.address=:80",
        "--entryPoints.http.http.middlewares=compress@docker",
        "--entryPoints.https.address=:443",
        "--api=true",
        "--api.insecure=true",
        "--api.dashboard=true",
        "--serversTransport.insecureSkipVerify=true",
        "--log=true",
        "--log.level=DEBUG",
        "--accessLog=true",
        "--accessLog.bufferingSize=100",
        "--accessLog.filters.statusCodes=400-499",
        "--providers.docker=true",
        "--providers.docker.endpoint=unix:///var/run/docker.sock",
        '--providers.docker.defaultrule=Host(`{{ index .Labels "com.docker.compose.service" }}.'
        + backplane["domain"]
        + "`)",
        "--providers.docker.exposedByDefault=true",
        "--providers.docker.constraints=Label(`backplane.enabled`,`true`)",
        "--providers.docker.network=backplane",
        "--providers.file.directory=/etc/traefik",
        "--providers.file.watch=true",
    ],
    "auto_remove": False,
    "detach": True,
    "healthcheck": {},
    "hostname": "backplane-traefik",
    "labels": {
        "backplane.enabled": "true",
        "traefik.http.routers.traefik.rule": "Host(`traefik."
        + backplane["domain"]
        + "`)",
        "traefik.http.middlewares.compress.compress": "true",
        "traefik.http.routers.traefik.service": "api@internal",
    },
    "name": "backplane-traefik",
    "network": "backplane",
    "ports": {"80/tcp": 80},
    "restart_policy": {"Name": "on-failure", "MaximumRetryCount": 5},
    "volumes": {
        "backplane-traefik-data": {"bind": "/letsencrypt", "mode": "rw"},
        "/var/run/docker.sock": {
            "bind": "/var/run/docker.sock",
            "mode": "ro",
        },
    },
}

backplane["services"]["traefik"]["options"] = {
    "ssl": {
        "command": [
            "--global.checkNewVersion=false",
            "--global.sendAnonymousUsage=false",
            "--entryPoints.http.address=:80",
            "--entryPoints.http.http.middlewares=compress@docker,https-redirect@docker"
            "--entryPoints.https.address=:443",
            "--entryPoints.https.http.middlewares=compress@docker,secured@docker",
            "--api=true",
            "--api.insecure=true",
            "--api.dashboard=true",
            "--serversTransport.insecureSkipVerify=true",
            "--log=true",
            "--log.level=DEBUG",
            "--accessLog=true",
            "--accessLog.bufferingSize=100",
            "--accessLog.filters.statusCodes=400-499",
            "--providers.docker=true",
            "--providers.docker.endpoint=unix:///var/run/docker.sock",
            '--providers.docker.defaultrule=Host(`{{ index .Labels "com.docker.compose.service" }}.'
            + backplane["domain"]
            + "`)",
            "--providers.docker.exposedByDefault=true",
            "--providers.docker.constraints=Label(`backplane.enabled`,`true`)",
            "--providers.docker.network=backplane",
            "--providers.file.directory=/etc/traefik",
            "--providers.file.watch=true",
            f"--certificatesresolvers.letsencrypt.acme.email={backplane['mail']}",
            "--certificatesresolvers.letsencrypt.acme.storage=/letsencrypt/acme.json",
            "--certificatesresolvers.letsencrypt.acme.httpchallenge.entrypoint=http",
        ],
        "ports": {"80/tcp": 80, "443/tcp": 443},
        "labels": {
            "backplane.enabled": "true",
            "traefik.http.routers.traefik.rule": "Host(`traefik."
            + backplane["domain"]
            + "`)",
            "traefik.http.middlewares.compress.compress": "true",
            "traefik.http.routers.traefik.service": "api@internal",
            "traefik.http.middlewares.secured.chain.middlewares": "https-redirect,default-whitelist,default-headers",
            "traefik.http.middlewares.https-redirect.redirectScheme.scheme": "https",
            "traefik.http.middlewares.https-redirect.redirectScheme.permanent": "true",
            "traefik.http.middlewares.default-whitelist.ipwhitelist.sourceRange": "10.0.0.0/8,192.168.0.0/16,127.0.0.1/32,172.0.0.0/8",
            "traefik.http.middlewares.default-headers.headers.frameDeny": "true",
            "traefik.http.middlewares.default-headers.headers.sslRedirect": "true",
            "traefik.http.middlewares.default-headers.headers.browserXssFilter": "true",
            "traefik.http.middlewares.default-headers.headers.contentTypeNosniff": "true",
            "traefik.http.middlewares.default-headers.headers.forceSTSHeader": "true",
            "traefik.http.middlewares.default-headers.headers.stsIncludeSubdomains": "true",
            "traefik.http.middlewares.default-headers.headers.stsPreload": "true",
            "traefik.http.routers.traefik-secured.service": "api@internal",
        },
    }
}

backplane["services"]["portainer"]["attrs"] = {
    "image": "portainer/portainer-ce:2.0.0",
    "auto_remove": False,
    "detach": True,
    "entrypoint": "/portainer -H unix:///var/run/docker.sock",
    "healthcheck": {},
    "hostname": "backplane-portainer",
    "labels": {
        "backplane.enabled": "true",
        "traefik.http.routers.portainer.rule": "Host(`portainer."
        + backplane["domain"]
        + "`)",
        "traefik.http.routers.http-portainer.service": "portainer",
        "traefik.http.services.portainer.loadbalancer.server.port": "9000",
    },
    "name": "backplane-portainer",
    "network": "backplane",
    "restart_policy": {"Name": "on-failure", "MaximumRetryCount": 5},
    "volumes": {
        "backplane-portainer-data": {"bind": "/data", "mode": "rw"},
        "/var/run/docker.sock": {
            "bind": "/var/run/docker.sock",
            "mode": "rw",
        },
    },
}

backplane["contexts_dir"] = os.getenv(
    "BACKPLANE_CONTEXTS_DIR", os.path.join(backplane["config_dir"], "contexts")
)
backplane["default_context_dir"] = os.path.join(
    backplane["contexts_dir"], backplane["default_context"]
)

backplane["contexts"] = {
    "default": {
        "directory": os.getenv(
            "BACKPLANE_DEFAULT_CONTEXT_DIR", backplane["default_context_dir"]
        )
    }
}

backplane["active_context_dir"] = backplane["default_context_dir"]


def getDynamicDomain(environment: str = backplane["environment"]):
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


@app.command()
def init(
    reinstall: bool = typer.Option(
        False, "--reinstall", "-r", help="Uninstall backplane first"
    ),
    domain: str = typer.Option(
        "",
        "--domain",
        "-d",
        help="The domain your backplane runs on",
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
    """
    Initialize backplane. Downloads the latest version of backplane.
    """
    error = False
    ssh_defaults = 'no-port-forwarding,no-X11-forwarding,no-agent-forwarding,no-pty,command="/usr/local/bin/backplane-ssh"'

    if reinstall:
        rm(force=True)

    # backplane['config_dir']
    if not os.path.exists(backplane["config_dir"]):
        if backplane["verbose"] > 0:
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
            if backplane["verbose"] > 0:
                typer.secho(
                    f"config directory {backplane['config_dir']} created",
                    err=False,
                    fg=typer.colors.GREEN,
                )

    else:
        if backplane["verbose"] > 0:
            typer.secho(
                f"config directory {backplane['config_dir']} exists",
                err=False,
                fg=typer.colors.GREEN,
            )

    # backplane['contexts_dir']
    if not os.path.exists(backplane["contexts_dir"]):
        if backplane["verbose"] > 0:
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
            if backplane["verbose"] > 0:
                typer.secho(
                    f"contexts directory {backplane['contexts_dir']} created",
                    err=False,
                    fg=typer.colors.GREEN,
                )

    else:
        if backplane["verbose"] > 0:
            typer.secho(
                f"contexts directory {backplane['contexts_dir']} exists",
                err=False,
                fg=typer.colors.GREEN,
            )

    # backplane['default_context_dir']
    if not os.path.exists(backplane["default_context_dir"]):
        if backplane["verbose"] > 0:
            typer.secho(
                f"default context directory {backplane['default_context_dir']} does not exist",
                err=True,
                fg=typer.colors.RED,
            )

        try:
            backplane_repo = os.getenv(
                "BACKPLANE_REPOSITORY", "https://github.com/wearep3r/backplane.git/"
            )
            clone_command = (
                f"git clone {backplane_repo} {backplane['default_context_dir']}"
            )
            clone = subprocess.call(clone_command, shell=True)

            if backplane["verbose"] > 0:
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

            if backplane["verbose"] > 0:
                typer.secho(f"{clone_command}", err=False, fg=typer.colors.BRIGHT_BLACK)

            error = True
            raise typer.Exit(code=1)
    else:
        if backplane["verbose"] > 0:
            typer.secho(
                f"default context directory {backplane['default_context_dir']} exists",
                err=False,
                fg=typer.colors.GREEN,
            )

    # make sure .env file exists
    if not os.path.exists(backplane["default_context_dir"] + "/.env"):
        if backplane["verbose"] > 0:
            typer.secho("default config does not exist", err=True, fg=typer.colors.RED)

        if not domain:
            backplane_domain = getDynamicDomain(environment)
        else:
            backplane_domain = domain

        try:
            # Generate special public format
            public_key = ""
            if ssh_public_key != "":
                public_key = f"{ssh_public_key}"
            else:
                with open(ssh_public_key_file, "r") as reader:
                    pubkey = reader.read().rstrip()
                    public_key = f"{pubkey}"

            env_file = [
                f"BACKPLANE_DOMAIN={backplane_domain}",
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
        if backplane["verbose"] > 0:
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
            if backplane["verbose"] > 0:
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
        if backplane["verbose"] > 0:
            typer.secho(
                "backplane Docker network exists", err=False, fg=typer.colors.GREEN
            )

    if not error:
        typer.secho(
            f"Installation successful. Use 'backplane up' to get going.",
            err=False,
            fg=typer.colors.GREEN,
        )
    else:
        typer.secho(
            f"Installation failed. Use 'backplane -v init' for verbose output.",
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
    down(remove=force, services=backplane["default_services"])

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
            "BACKPLANE_REPOSITORY", "https://github.com/wearep3r/backplane.git"
        )
        pull_command = f"git pull origin master"
        pull = subprocess.call(
            pull_command, shell=True, cwd=backplane["default_context_dir"]
        )

        typer.secho(f"Successfully updated backplane", err=False, fg=typer.colors.GREEN)

        down()
        up()
    except Exception as e:
        typer.secho(f"Failed to update backplane: {e}", err=True, fg=typer.colors.RED)

        if backplane["verbose"] > 0:
            typer.secho(f"{pull_command}", err=False, fg=typer.colors.BRIGHT_BLACK)

        raise typer.Exit(code=1)


def getService(service: str):
    # docker_compose_command = f"docker-compose -f docker-compose.yml -p backplane-{service} up -d --remove-orphans"
    # project_dir = os.path.join(
    #     backplane["active_context_dir"], service, backplane["environment"]
    # )
    # result = runCommand(docker_compose_command, project_dir)
    docker_client = docker.from_env()
    container = None

    try:
        service_name = backplane["services"][service]["attrs"]["name"]
        containers = docker_client.containers.list(
            all=True, filters={"name": service_name}
        )

        # no containers for our service are running
        if containers:
            container = docker_client.containers.get(service_name)
            return container
        else:
            return None
    except docker.errors.APIError as e:
        typer.secho(
            f"Failed to get {service}: {e}",
            err=True,
            fg=typer.colors.RED,
        )
        sys.exit(1)


def startService(service):
    # docker_compose_command = f"docker-compose -f docker-compose.yml -p backplane-{service} up -d --remove-orphans"
    # project_dir = os.path.join(
    #     backplane["active_context_dir"], service, backplane["environment"]
    # )
    # result = runCommand(docker_compose_command, project_dir)
    docker_client = docker.from_env()

    existing_service = getService(service)
    try:
        if not existing_service:
            container = docker_client.containers.run(
                **backplane["services"][service]["attrs"]
            )
        else:
            container = existing_service
        return container
    except Exception as e:
        typer.secho(
            f"Failed to start {service.name}: {e}",
            err=True,
            fg=typer.colors.RED,
        )
        sys.exit(1)


def stopService(service, delete: bool = True, prune: bool = False):
    try:
        if service:
            service_name = service.name
            if service.status == "running":
                service.stop()

            if delete:
                service.remove()

            if prune:
                docker_client = docker.from_env()

                volume = docker_client.volumes.get(f"{service_name}-data")
                volume.remove(force=True)

        return True
    except Exception as e:
        typer.secho(
            f"Failed to stop {service.name}: {e}",
            err=True,
            fg=typer.colors.RED,
        )
        sys.exit(1)


@app.command()
def up(
    services: str = typer.Option(
        backplane["default_services"],
        "--services",
        "-s",
        help="Comma-separated list of services to start.",
    ),
    restart: bool = typer.Option(False, "--restart", "-r", help="Restart services"),
):
    """
    Start backplane. Starts all services.
    """

    backplane_services = services.split(",")

    for service in backplane_services:
        existing_service = getService(service)

        if existing_service and restart:
            stopService(service=existing_service, delete=True)

        container = startService(service)

        time.sleep(2)

        printStatus(container, service)


def printStatus(container, service):
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
                f"http://{backplane['services'][service]['domain']}",
                fg=typer.colors.BLUE,
            ),
        ]
        output = output + message_url

    typer.echo("".join(output))

    # local_indent = backplane_echo_indent * 3
    # typer.echo(f"{local_indent}Name: {container['name'].strip('/')}")
    # typer.echo(f"{local_indent}ID: {container['id']}")
    # typer.echo(f"{local_indent}Image: {container['image']}")
    # typer.echo(f"{local_indent}Restarts: {container['restarts']}")


@app.command()
def restart(
    services: str = typer.Option(
        backplane["default_services"],
        "--services",
        "-s",
        help="Comma-separated list of services to restart",
    ),
):
    """
    Restart services.
    """
    up(service=services, restart=True)


@app.command()
def down(
    services: str = typer.Option(
        backplane["default_services"],
        "--services",
        "-s",
        help="Comma-separated list of services to stop",
    ),
    prune: bool = typer.Option(False, "--prune", "-p", help="Remove volumes"),
):
    """
    Stop backplane. Stops all services.
    """
    backplane_services = services.split(",")

    for service in backplane_services:
        existing_service = getService(service)
        stopService(service=existing_service, delete=True, prune=prune)


@app.command()
def status(
    services: str = typer.Option(
        backplane["default_services"],
        "--services",
        "-s",
        help="Comma-separated list of services to get status for",
    ),
):
    """
    backplane status.
    """
    backplane_services = services.split(",")

    for service in backplane_services:
        existing_service = getService(service)

        if existing_service:
            printStatus(existing_service, service)
        else:
            message_name = typer.style(f"backplane-{service}: ", bold=True)
            message_prefix = typer.style(" ∟ ", fg=typer.colors.RED)
            message_status = typer.style(
                f"missing", fg=typer.colors.WHITE, bg=typer.colors.RED
            )
            message_info = typer.style(f" (HINT: run 'backplane up' to start {service})")
            output = [message_prefix, message_name, message_status, message_info]
            typer.echo("".join(output))


@app.command()
def logs(
    services: str = typer.Option(
        backplane["default_services"],
        "--services",
        "-s",
        help="Comma-separated list of services to get logs for",
    )
):
    """
    backplane logs. Shows logs for all services.
    """
    backplane_services = services.split(",")

    for service in backplane_services:
        for container_id in getContainerIDs(service):
            if container_id != "":
                docker_client = docker.from_env()
                container = docker_client.containers.get(container_id)

                if backplane["verbose"] > 0:
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


@app.command()
def context(context: Optional[str] = typer.Argument("default")):
    _active_context = os.path.join(backplane["config_dir"], ".active_context")
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
            with open(
                os.path.join(backplane["config_dir"], ".active_context"), "r"
            ) as reader:
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
            with open(
                os.path.join(backplane["config_dir"], ".active_context"), "r+"
            ) as writer:
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
    config_file: str = typer.Option(
        os.path.join(backplane["active_context_dir"], "backplane.yml"),
        "--config-file",
        "-c",
        help="Path to backplane.yml",
    ),
):
    checkPrerequisites(ctx)

    backplane["verbose"] = verbose

    # LOAD CONFIG HERE
    # backplane_config = anyconfig.load(config_file)

    if backplane["verbose"] > 0:
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
