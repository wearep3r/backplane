from .config import Config
from .errors import (
    ConfigNotFound,
    ServiceNotFound,
    CannotStartService,
    CannotStopService,
    CannotRemoveService,
)
import docker
import time
import typer
import os
from read_version import read_version


class Service:
    config = Config()

    def __init__(self, name=None, config=None):
        self.config = config
        self.name = name

        self.url = f"{self.name}.{self.config.domain}"
        self.start_timeout = 90

        self.container = None
        self.options = None

        self.populateConfig()

        self._status()

    def populateConfig(self):
        if self.name == "traefik":
            self.attrs = {
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
                    + self.config.domain + "`)",
                    "--providers.docker.exposedByDefault=true",
                    "--providers.docker.constraints=Label(`backplane.enabled`,`true`)",
                    "--providers.docker.network=backplane",
                    "--providers.file.directory=/etc/traefik",
                    "--providers.file.watch=true",
                ],
                "auto_remove": False,
                "detach": True,
                "hostname": "traefik",
                "labels": {
                    "backplane.enabled": "true",
                    "backplane.service": "traefik",
                    "backplane.url": self.url,
                    "traefik.http.routers.traefik.rule": "Host(`" + self.url + "`)",
                    "traefik.http.middlewares.compress.compress": "true",
                    "traefik.http.middlewares.auth.basicauth.users": f"{self.config.user}:{self.config.password_hash}",
                    "traefik.http.middlewares.auth.basicauth.realm": "backplane",
                    "traefik.http.routers.traefik.service": "api@internal",
                },
                "name": "traefik",
                "network": "backplane",
                "ports": {"80/tcp": 80},
                "restart_policy": {"Name": "unless-stopped"},
                "volumes": {
                    "traefik-data": {"bind": "/letsencrypt", "mode": "rw"},
                    "/var/run/docker.sock": {
                        "bind": "/var/run/docker.sock",
                        "mode": "ro",
                    },
                },
            }
            self.options = {
                "https": {
                    "command": [
                        "--global.checkNewVersion=false",
                        "--global.sendAnonymousUsage=false",
                        "--entryPoints.http.address=:80",
                        "--entryPoints.http.http.redirections.entryPoint.to=https",
                        "--entryPoints.http.http.redirections.entryPoint.scheme=https",
                        "--entryPoints.http.http.middlewares=compress@docker",
                        "--entryPoints.https.address=:443",
                        "--entryPoints.https.http.middlewares=compress@docker,secured@docker",
                        "--entryPoints.https.http.tls.certResolver=letsencrypt",
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
                        + self.config.domain
                        + "`)",
                        "--providers.docker.exposedByDefault=true",
                        "--providers.docker.constraints=Label(`backplane.enabled`,`true`)",
                        "--providers.docker.network=backplane",
                        "--providers.file.directory=/etc/traefik",
                        "--providers.file.watch=true",
                        f"--certificatesresolvers.letsencrypt.acme.email={self.config.mail}",
                        "--certificatesresolvers.letsencrypt.acme.storage=/letsencrypt/acme.json",
                        "--certificatesresolvers.letsencrypt.acme.httpchallenge.entrypoint=http",
                    ],
                    "ports": {"80/tcp": 80, "443/tcp": 443},
                    "labels": {
                        "backplane.enabled": "true",
                        "traefik.http.routers.traefik.rule": "Host(`" + self.url + "`)",
                        "traefik.http.middlewares.compress.compress": "true",
                        "traefik.http.routers.traefik.service": "api@internal",
                        "traefik.http.routers.traefik.middlewares": "auth@docker",
                        "traefik.http.middlewares.secured.chain.middlewares": "default-headers",
                        "traefik.http.middlewares.https-redirect.redirectScheme.scheme": "https",
                        "traefik.http.middlewares.https-redirect.redirectScheme.permanent": "true",
                        # "traefik.http.middlewares.default-whitelist.ipwhitelist.sourceRange": "10.0.0.0/8,192.168.0.0/16,127.0.0.1/32,172.0.0.0/8",
                        "traefik.http.middlewares.auth.basicauth.users": f"{self.config.user}:{self.config.password_hash}",
                        "traefik.http.middlewares.auth.basicauth.realm": "backplane",
                        "traefik.http.middlewares.default-headers.headers.frameDeny": "true",
                        "traefik.http.middlewares.default-headers.headers.sslRedirect": "true",
                        "traefik.http.middlewares.default-headers.headers.browserXssFilter": "true",
                        "traefik.http.middlewares.default-headers.headers.contentTypeNosniff": "true",
                        "traefik.http.middlewares.default-headers.headers.forceSTSHeader": "false",
                        "traefik.http.middlewares.default-headers.headers.stsIncludeSubdomains": "false",
                        "traefik.http.middlewares.default-headers.headers.stsPreload": "false",
                        "traefik.http.middlewares.default-headers.headers.sslProxyHeaders.X-FORWARDED-PROTO": "https",
                        "traefik.http.routers.traefik-secured.service": "api@internal",
                        "traefik.http.routers.traefik-secured.tls": "true",
                        "traefik.http.routers.traefik-secured.rule": "Host(`"
                        + self.url
                        + "`)",
                        "traefik.http.routers.traefik-secured.middlewares": "auth@docker",
                    },
                }
            }
        elif self.name == "portainer":
            self.attrs = {
                "image": "portainer/portainer-ce:2.0.0",
                "auto_remove": False,
                "detach": True,
                "entrypoint": f"/portainer -H unix:///var/run/docker.sock --templates {self.config.template_url} --admin-password {self.config.password_hash}",
                "hostname": "portainer",
                "labels": {
                    "backplane.enabled": "true",
                    "traefik.http.routers.portainer.rule": "Host(`" + self.url + "`)",
                    "traefik.http.services.portainer.loadbalancer.server.port": "9000",
                },
                "name": "portainer",
                "ports": {"8000/tcp": 8000},
                "network": "backplane",
                "restart_policy": {"Name": "unless-stopped"},
                "volumes": {
                    "portainer-data": {"bind": "/data", "mode": "rw"},
                    "/var/run/docker.sock": {
                        "bind": "/var/run/docker.sock",
                        "mode": "rw",
                    },
                },
            }

            self.options = {
                "https": {
                    "labels": {
                        "backplane.enabled": "true",
                        "traefik.http.routers.portainer.rule": "Host(`" + self.url + "`)",
                        "traefik.http.services.portainer.loadbalancer.server.port": "9000",
                        "traefik.http.routers.portainer-secured.tls": "true",
                        "traefik.http.routers.portainer-secured.rule": "Host(`"
                        + self.url
                        + "`)",
                    },
                }
            }

        elif self.name == "backplane":
            self.attrs = {
                "image": f"wearep3r/backplane:{read_version('.', '__init__.py')}",
                "auto_remove": False,
                "detach": True,
                "command": "ssh",
                "hostname": "backplane",
                "labels": {},
                "name": "backplane",
                "network": "backplane",
                "ports": {"2222/tcp": 2222},
                "environment": {
                    "BACKPLANE_DOMAIN": self.config.domain,
                    "BACKPLANE_MAIL": self.config.mail,
                },
                "restart_policy": {"Name": "unless-stopped"},
                "volumes": {
                    f"{os.path.join(os.getenv('HOME'),'.ssh')}": {
                        "bind": "/ssh",
                        "mode": "ro",
                    },
                    "backplane-repositories": {
                        "bind": "/backplane/repositories",
                        "mode": "rw",
                    },
                    f"{os.path.join(self.config.config_dir)}": {
                        "bind": "/backplane/.backplane",
                        "mode": "rw",
                    },
                    "/var/run/docker.sock": {
                        "bind": "/var/run/docker.sock",
                        "mode": "rw",
                    },
                },
            }

        else:
            raise ServiceNotFound(f"service {self.name} does not exist")

        # Rewrite https config
        if self.config.https:
            if self.options:
                if "https" in self.options:
                    for key in self.options["https"].keys():
                        self.attrs[key] = self.options["https"][key]

    def _status(self):
        docker_client = docker.from_env()

        try:
            containers = docker_client.containers.list(
                all=True, filters={"name": self.name}
            )

            # no containers for our service are running
            if containers:
                c = None
                for container in containers:
                    if container.attrs["Name"].strip("/") == self.name:
                        c = container
                self.container = c

        except Exception as e:
            raise ServiceNotFound(
                f"Unable to locate container for service {self.name}: {e}"
            )

    def echo(self, nl=True):
        # Target message:
        # [traefik] running at http://traefik.127-0-0-1.ns0.co
        message_prefix = typer.style(f"{self.name} ", bold=True)
        # message_prefix = typer.style(" ∟ ", fg=typer.colors.RED)

        if self.container:
            if self.container.attrs["State"]["Status"] == "running":
                message_status = typer.style("running", fg=typer.colors.GREEN, bold=True)

                if self.name != "backplane":
                    url_prefix = "https://" if self.config.https else "http://"
                    message_info = typer.style(f" ({url_prefix}{self.url})")
                else:
                    message_info = ""
            elif self.container.attrs["State"]["Status"] == "starting":
                message_status = typer.style(
                    "starting", fg=typer.colors.WHITE, bg=typer.colors.BLUE
                )
            elif self.container.attrs["State"]["Status"] == "exited":
                message_status = typer.style(
                    "exited", fg=typer.colors.WHITE, bg=typer.colors.RED
                )
                message_info = typer.style(
                    f" (HINT: run 'backplane up' to start {self.name})"
                )
            elif self.container.attrs["State"]["Status"] == "dead":
                message_status = typer.style(
                    "dead", fg=typer.colors.WHITE, bg=typer.colors.BRIGHT_RED
                )
            elif self.container.attrs["State"]["Status"] == "created":
                message_status = typer.style(
                    "created", fg=typer.colors.WHITE, bg=typer.colors.BRIGHT_BLACK
                )
                message_info = typer.style(
                    f" (HINT: run 'backplane up' to start {self.name})"
                )
            elif self.container.attrs["State"]["Status"] == "paused":
                message_status = typer.style(
                    "paused", fg=typer.colors.WHITE, bg=typer.colors.MAGENTA
                )
                message_info = typer.style(
                    f" (HINT: run 'backplane up' to start {self.name})"
                )
        else:
            message_status = typer.style(
                "missing", fg=typer.colors.WHITE, bg=typer.colors.RED
            )
            message_info = typer.style(
                f" (HINT: run 'backplane up' to start {self.name})"
            )

        output = [message_prefix, message_status, message_info]

        if not nl:
            output.append("\r")

        typer.echo("".join(output), nl=nl)

    def start(self):
        docker_client = docker.from_env()
        if not self.container:
            try:
                self.container = docker_client.containers.run(**self.attrs)

                self.wait()

            except Exception as e:
                raise CannotStartService(
                    f"Unable to start container for service {self.name}: {e}"
                )

        else:
            if self.container.attrs["State"]["Status"] != "running":
                self.container.start()
                self.wait()

    def stop(self):
        if self.container:
            try:
                self.container.stop()
                self.wait("exited")
            except Exception as e:
                raise CannotStopService(
                    f"Unable to stop container for service {self.name}: {e}"
                )

    def remove(self, prune: bool = False):
        if self.container:
            try:
                self.stop()
                self.container.remove()
                self.container = None

                if prune:
                    # Remove volumes
                    docker_client = docker.from_env()

                    volumes = docker_client.volumes.list(filters={"name": self.name})

                    if volumes:
                        for volume in volumes:
                            if volume.attrs["Name"].strip("/") == f"{self.name}-data":
                                # volume = docker_client.volumes.get(f"{self.name}-data")
                                volume.remove(force=True)

            except Exception as e:
                raise CannotRemoveService(
                    f"Unable to remove container for service {self.name}: {e}"
                )

    def wait(self, status: str = "running"):
        retries = 0
        while (
            self.container.attrs["State"]["Status"] != status
            and retries < self.start_timeout
        ):
            self.container.reload()
            time.sleep(1)
            retries += 1
            typer.echo(
                f"Waiting for service {self.name} to become {status} ({self.start_timeout-retries})\r",
                nl=False,
            )
        return True
