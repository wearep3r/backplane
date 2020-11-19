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


class Service:
    config = Config()

    def __init__(self, name=None, config=None):
        self.config = config
        self.name = name

        self.url = f"{self.name}.{self.config.domain}"
        self.start_timeout = 90

        self.container = None

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
                    "traefik.http.routers.traefik.service": "api@internal",
                },
                "name": "traefik",
                "network": "backplane",
                "ports": {"80/tcp": 80},
                "restart_policy": {"Name": "on-failure", "MaximumRetryCount": 5},
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
                    # "healthcheck": {
                    #     "test": [
                    #         "CMD",
                    #         "wget",
                    #         "--no-verbose",
                    #         "--tries=1",
                    #         "--spider",
                    #         "http://localhost/ping",
                    #     ],
                    #     "interval": "1m30s",
                    #     "timeout": "10s",
                    #     "retries": 3,
                    #     "start_period": "1s",
                    # },
                    "labels": {
                        "backplane.enabled": "true",
                        "traefik.http.routers.traefik.rule": "Host(`traefik."
                        + self.url
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
            # Rewrite https config
            if self.config.https:
                for key in self.options["https"].keys():
                    self.attrs[key] = self.options["https"][key]
        elif self.name == "portainer":
            self.attrs = {
                "image": "portainer/portainer-ce:2.0.0",
                "auto_remove": False,
                "detach": True,
                "entrypoint": f"/portainer -H unix:///var/run/docker.sock --templates {self.config.template_url}",
                "hostname": "portainer",
                "labels": {
                    "backplane.enabled": "true",
                    "traefik.http.routers.portainer.rule": "Host(`" + self.url + "`)",
                    "traefik.http.services.portainer.loadbalancer.server.port": "9000",
                },
                "name": "portainer",
                "network": "backplane",
                "restart_policy": {"Name": "on-failure", "MaximumRetryCount": 5},
                "volumes": {
                    "portainer-data": {"bind": "/data", "mode": "rw"},
                    "/var/run/docker.sock": {
                        "bind": "/var/run/docker.sock",
                        "mode": "rw",
                    },
                },
            }
        elif self.name == "shipmate":
            pass
        else:
            raise ServiceNotFound(f"service {self.name} does not exist")

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
        # [traefik] running at http://traefik.127-0-0-1.nip.io
        message_prefix = typer.style(f"{self.name} ", bold=True)
        # message_prefix = typer.style(" ∟ ", fg=typer.colors.RED)

        if self.container:
            if self.container.attrs["State"]["Status"] == "running":
                message_status = typer.style("running", fg=typer.colors.GREEN, bold=True)
                url_prefix = "https://" if self.config.https else "http://"
                message_info = typer.style(f" ({url_prefix}{self.url})")
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
                print(self.attrs)
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

                if prune:
                    # Remove volumes
                    docker_client = docker.from_env()

                    volume = docker_client.volumes.get(f"{self.name}-data")
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
