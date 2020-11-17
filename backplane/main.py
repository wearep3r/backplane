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
from typing import Optional, List
import time
import utils
import pkg_resources  # part of setuptools
from read_version import read_version
import pprint

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

backplane = {
    "config_dir": os.getenv(
        "BACKPLANE_CONIG_DIR", os.path.join(os.getenv("HOME", "~"), ".backplane")
    ),
    "default_context": "default",
    "active_context": "default",
    "environment": "development",
    "domain": "127-0-0-1.nip.io",
    "mail": "",
    "default_services": ["traefik", "portainer"],
    "verbose": False,
    "ssh_public_key": None,
    "ssh_public_key_file": f"{os.getenv('HOME')}/.ssh/id_rsa.pub",
    "https": False,
}

backplane["services"] = {
    "traefik": {"url": f"traefik.{backplane['domain']}", "start_timeout": 30},
    "portainer": {"url": f"portainer.{backplane['domain']}", "start_timeout": 30},
}

# Attributes
backplane["services"]["traefik"]["attrs"] = {
    "image": "traefik:v2.3",
    "command": [
        "--global.checkNewVersion=false",
        "--global.sendAnonymousUsage=false",
        "--entryPoints.http.address=:80",
        "--entryPoints.http.http.middlewares=compress@docker",
        # "--entryPoints.https.address=:443",
        "--api=true",
        "--api.insecure=true",
        "--api.dashboard=true",
        "--ping=true",
        "--serversTransport.insecureSkipVerify=true",
        "--log=true",
        "--log.level=DEBUG",
        "--accessLog=true",
        "--accessLog.bufferingSize=100",
        "--accessLog.filters.statusCodes=400-499",
        "--providers.docker=true",
        "--providers.docker.endpoint=unix:///var/run/docker.sock",
        '--providers.docker.defaultrule=Host(`{{ index .Labels "com.docker.compose.service" }}.'
        # "--providers.docker.defaultrule=Host(`{{ normalize .Container.Name }}."
        + backplane["domain"] + "`)",
        "--providers.docker.exposedByDefault=true",
        "--providers.docker.constraints=Label(`backplane.enabled`,`true`)",
        "--providers.docker.network=backplane",
        "--providers.file.directory=/etc/traefik",
        "--providers.file.watch=true",
    ],
    "auto_remove": False,
    "detach": True,
    "hostname": "backplane-traefik",
    "labels": {
        "backplane.enabled": "true",
        "backplane.service": "traefik",
        "backplane.url": backplane["services"]["traefik"]["url"],
        "traefik.http.routers.traefik.rule": "Host(`"
        + backplane["services"]["traefik"]["url"]
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
    "https": {
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
            "--ping=true",
            "--ping.entrypoint=http",
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
        "healthcheck": {
            "test": [
                "CMD",
                "wget",
                "--no-verbose",
                "--tries=1",
                "--spider",
                "http://localhost/ping",
            ],
            "interval": "1m30s",
            "timeout": "10s",
            "retries": 3,
            "start_period": "1s",
        },
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
    # "healthcheck": {
    #     "test": [
    #         "CMD",
    #         "wget",
    #         "--no-verbose",
    #         "--tries=1",
    #         "--spider",
    #         "http://localhost:8080/ping",
    #     ],
    #     "interval": 90000000000,
    #     "timeout": 10000000000,
    #     "retries": 3,
    #     "start_period": 5000000000,
    # },
    "hostname": "backplane-portainer",
    "labels": {
        "backplane.enabled": "true",
        "traefik.http.routers.portainer.rule": "Host(`"
        + backplane["services"]["portainer"]["url"]
        + "`)",
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
    Initialize backplane.
    """

    if reinstall:
        rm(force=True)

    # Create config dir
    utils.createDir(backplane["config_dir"])

    # Create contexts dir
    utils.createDir(backplane["contexts_dir"])

    # Create default context dir
    utils.createDir(backplane["default_context_dir"])

    # Create Docker network
    utils.createNetwork("backplane")

    # Prepare custom config
    backplane_config = {}
    backplane_config_dir = f"{backplane['active_context_dir']}/backplane.yml"

    if https:
        backplane_config["https"] = True

    # A custom domain has been set
    if domain:
        backplane_config["domain"] = domain

    # A custom mail has been set
    if mail:
        backplane_config["mail"] = mail

    if ssh_public_key:
        backplane_config["ssh_public_key"] = ssh_public_key

    if ssh_public_key_file:
        backplane_config["ssh_public_key_file"] = ssh_public_key_file

    if backplane_config:
        utils.writeConfig(backplane_config_dir, backplane_config)
        if backplane["verbose"] > 0:
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
    utils.rmDir(backplane["config_dir"])

    # Remove network
    utils.rmNetwork("backplane")

    typer.secho("Successfully uninstalled backplane", err=False, fg=typer.colors.GREEN)


def getService(service: str):
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
    except Exception as e:
        typer.secho(
            f"Failed to get {service}: {e}",
            err=True,
            fg=typer.colors.RED,
        )
        sys.exit(1)


def mkService(service):
    docker_client = docker.from_env()

    existing_service = getService(service)
    try:
        if not existing_service:
            if backplane["verbose"] > 0:
                typer.secho(
                    f"mkService: creating service {service}",
                    err=False,
                    fg=typer.colors.BRIGHT_BLACK,
                )
                typer.secho(
                    f"mkService: service config: {backplane['services'][service]['attrs']}",
                    err=False,
                    fg=typer.colors.BRIGHT_BLACK,
                )
            container = docker_client.containers.run(
                **backplane["services"][service]["attrs"]
            )
            if backplane["verbose"] > 0:
                typer.secho(
                    f"mkService: created service {service}",
                    err=False,
                    fg=typer.colors.BRIGHT_BLACK,
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


def rmService(service, delete: bool = True, prune: bool = False):
    try:
        if service:
            service_name = service.name
            if service.status == "running":
                if backplane["verbose"] > 0:
                    typer.secho(
                        f"rmService: stopping service {service_name}",
                        err=False,
                        fg=typer.colors.BRIGHT_BLACK,
                    )
                service.stop()

            if delete:
                if backplane["verbose"] > 0:
                    typer.secho(
                        f"rmService: removing service {service_name}",
                        err=False,
                        fg=typer.colors.BRIGHT_BLACK,
                    )
                service.remove()

            if prune:
                docker_client = docker.from_env()

                if backplane["verbose"] > 0:
                    typer.secho(
                        f"rmService: removing volumes for service {service_name}",
                        err=False,
                        fg=typer.colors.BRIGHT_BLACK,
                    )

                volume = docker_client.volumes.get(f"{service_name}-data")
                volume.remove(force=True)

        return True
    except Exception as e:
        typer.secho(
            f"rmService: failed to stop {service.name}: {e}",
            err=True,
            fg=typer.colors.RED,
        )
        sys.exit(1)


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
        services = backplane["default_services"]
    else:
        services = [service]

    for service in services:
        if backplane["verbose"] > 0:
            typer.secho(
                f"up: starting {service}",
                err=False,
                fg=typer.colors.BRIGHT_BLACK,
            )

        if restart:
            existing_service = getService(service)
            if existing_service:
                if backplane["verbose"] > 0:
                    typer.secho(
                        f"up: stopping service {service}",
                        err=False,
                        fg=typer.colors.BRIGHT_BLACK,
                    )
                rmService(service=existing_service, delete=True)

        container = mkService(service)

        if container:
            if backplane["verbose"] > 0:
                typer.secho(
                    f"up: started service {service}",
                    err=False,
                    fg=typer.colors.BRIGHT_BLACK,
                )
        else:
            if backplane["verbose"] > 0:
                typer.secho(
                    f"up: failed to start service {service}",
                    err=False,
                    fg=typer.colors.BRIGHT_BLACK,
                )
            sys.exit(1)

        retries = 0
        while (
            container.status != "running"
            and retries < backplane["services"][service]["start_timeout"]
        ):
            time.sleep(1)
            retries += 1

            message_name = typer.style(f"{container.name.strip('/')}: ", bold=True)

            message_prefix = typer.style(" ∟ ", fg=typer.colors.BLUE)
            message_status = typer.style(
                f"{container.status}", fg=typer.colors.WHITE, bg=typer.colors.BLUE
            )

            message_wait = typer.style(
                f" (waiting {backplane['services'][service]['start_timeout']-retries} more seconds)"
            )

            output = [message_prefix, message_name, message_status, message_wait, "\r"]

            typer.echo("".join(output), nl=False)

            container.reload()

        utils.printStatus(container, service, backplane)


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

    if backplane["verbose"] > 0:
        typer.secho(
            f"Shutting down {service}",
            err=False,
            fg=typer.colors.BRIGHT_BLACK,
        )

    backplane_service = service

    if not backplane_service:
        services = backplane["default_services"]
    else:
        services = [backplane_service]

    for service in services:
        existing_service = getService(service)
        rmService(service=existing_service, delete=True, prune=prune)


def getConfig():
    config = utils.readConfig(
        f"{backplane['active_context_dir']}/backplane.yml", backplane
    )
    return config


@app.command()
def config():
    config = getConfig()

    if backplane["verbose"] > 0:
        typer.secho(
            f"Loaded user config from {backplane['active_context_dir']}/backplane.yml",
            err=False,
            fg=typer.colors.BRIGHT_BLACK,
        )

    typer.secho(
        json.dumps(config, indent=4, sort_keys=True),
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
        services = backplane["default_services"]
    else:
        services = [service]

    for service in services:
        existing_service = getService(service)

        if existing_service:
            utils.printStatus(existing_service, service, backplane)
        else:
            message_name = typer.style(f"backplane-{service}: ", bold=True)
            message_prefix = typer.style(" ∟ ", fg=typer.colors.RED)
            message_status = typer.style(
                "missing", fg=typer.colors.WHITE, bg=typer.colors.RED
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
        version = read_version(".", "__init__.py")
        typer.echo(f"backplane CLI: {version}")
        raise typer.Exit()


def checkPrerequisites(ctx):
    # Check for Docker
    if not which("docker"):
        typer.secho("Docker not installed", err=True, fg=typer.colors.RED)
        raise typer.Abort()

    if not os.path.exists(backplane["config_dir"]):
        if ctx.invoked_subcommand == "init":
            pass
        else:
            typer.secho(
                "config directory missing. Run 'backplane init' first.",
                err=True,
                fg=typer.colors.RED,
            )
            sys.exit(1)

    if not os.path.exists(backplane["active_context_dir"]):
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

    backplane = getConfig()

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
