import os
import validators
from pathlib import Path, PosixPath
import anyconfig
from git.repo.base import Repo
from . import utils
import sys
import json
from json import JSONEncoder
import typer
import subprocess
from .config import Config
from .errors import (
    ConfigNotFound,
    ServiceNotFound,
    CannotStartService,
    CannotStopService,
    CannotRemoveService,
    CannotInstallApp,
)


class CustomEncoder(JSONEncoder):
    def default(self, o):
        if isinstance(o, PosixPath):
            return str(o)


class App:
    def __init__(
        self,
        name: str,
        path: Path,
        url: str = None,
        config: Config = None,
    ):
        if config:
            self.config = config
        else:
            raise ConfigNotFound("No config given to app")

        if not name:
            raise ConfigNotFound("No name given to app")

        self.name: str = name
        self.path: Path = path
        self.url: str = url

    def install(self):
        if not self.path.exists():
            raise CannotInstallApp(f"{self.path} no found")

        # 2. Run the app
        # - load compose config w/ anyconf
        # - check if build needed
        # if self.url:
        #         try:
        #             Repo.clone_from(self.url, self.path)

        # Save app to config
        if self.config:
            custom_config = {"apps": {}}
            custom_config["apps"][self.name] = {"path": self.path, "params": {}}

            self.config.write(custom_config)

            if self.config.verbose > 0:
                typer.secho(
                    f"Saving new config to {self.config.config_path}",
                    err=False,
                    fg=typer.colors.BRIGHT_BLACK,
                )
        try:
            install_command = [
                "docker-compose",
                "-p",
                self.name,
            ]

            if self.config.verbose:
                install_command.append("--verbose")

            env_file = self.path / ".env"
            if env_file.exists():
                install_command.append("--env-file")
                install_command.append(str(env_file))

            compose_file = self.path / "docker-compose.yml"
            app_config = {}
            if compose_file.exists():
                install_command.append("-f")
                install_command.append(str(compose_file))

                # Load config
                app_config = anyconfig.load(compose_file)
            else:
                raise CannotInstallApp(f"{compose_file} not found")

            install_command.append("up")
            install_command.append("-d")

            # Check if build is necessary
            build = False
            for service in app_config["services"]:
                service_config = app_config["services"][service]
                if "build" in service_config:
                    build = True

            if build:
                install_command.append("--build")
                install_command.append("--force-recreate")
                os.environ["DOCKER_BUILDKIT"] = "1"

            if self.config.verbose > 0:
                print(f"install command: {' '.join(install_command)}")

            # Start installation
            try:
                result = subprocess.Popen(install_command, stdout=subprocess.PIPE)
                while True:
                    try:
                        output = next(result.stdout)
                        typer.echo(output.decode().strip())
                    except StopIteration:
                        # Get returncode from process
                        result.communicate()[0]
                        break

                if result.returncode == 0:
                    print("Deployment complete.")

                    # Get logs
                    logs_command = [
                        "docker-compose",
                        "-p",
                        self.name,
                        "-f",
                        compose_file,
                        "logs",
                        "--tail",
                        "50",
                    ]
                    result = subprocess.Popen(logs_command, stdout=subprocess.PIPE)
                    while True:
                        try:
                            output = next(result.stdout)
                            typer.echo(output.decode().strip())
                        except StopIteration:
                            print("Logs complete.")
                            break
                else:
                    raise CannotInstallApp(
                        f"Deployment failed with code {result.returncode}."
                    )

            except Exception as e:
                raise CannotInstallApp(f"failed to install {self.name}: {e}")
        except Exception as e:
            raise CannotInstallApp(f"failed to install {self.name}: {e}")

    def serialize(self):
        current_config = dict(self.__dict__)
        return CustomEncoder().encode(current_config)

    def toJSON(self):
        return self.serialize()

    def toDict(self):
        return json.loads(self.serialize())

    def load(self):
        try:
            if self.config_path.exists() and self.config_path.is_file():
                current_config = self.toDict()
                custom_config = anyconfig.load([str(self.config_path)])
                anyconfig.merge(current_config, custom_config)

                self.__dict__ = current_config
                return current_config
            # else:
            #    raise ConfigNotFound
            pass
        except anyconfig.globals.UnknownFileTypeError as e:
            raise ConfigNotFound(e)
        except FileNotFoundError as e:
            raise ConfigNotFound(e)

    def dump(self):
        # Serialize as string by default (types like Path
        # can't be serialized by JSONEncoder by default)
        return json.dumps(dict(self.__dict__), indent=4, sort_keys=True, default=str)

    def write(self):
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
