import os
import validators
from typing import List, Optional
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
import datetime
from read_version import read_version
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
        config: Config = None,
        source: str = None,
        compose_file: Optional[List[str]] = None,
    ):
        if config:
            self.config = config
        else:
            raise ConfigNotFound("No config given to app")

        if not name:
            raise ConfigNotFound("No name given to app")

        self.name: str = name
        self.path: Path = path
        self.source: str = source
        self.compose_file: str = compose_file

    def install(self):
        if not self.path.exists():
            raise CannotInstallApp(f"{self.path} not found")

        if not self.config:
            raise CannotInstallApp("No config given")

        # If a name is give but no source,
        # first: check if there's an installed app by that name in backplane.yml and update it
        # second: check if an app with that name exists in the app store (https://github.com/backplane-apps) and install it

        if self.name in self.config.apps:
            # app has been installed before
            # set self.source to app's source
            self.source = self.config.apps[self.name]["source"]
        else:
            # Name is given
            if not self.source:
                # No source is given
                # Set self.source to app-store url
                self.source = f"{self.config.appstore_url}/{self.name}"
            else:
                pass

        # Check if --source is given
        # If yes, download and install app from source to app_dir/self.name
        if self.source:
            # Loading app from external source

            app_path = os.path.join(self.config.app_dir, self.name)
            cwd = os.getcwd()

            try:
                # Check if app already exists
                if os.path.exists(app_path):
                    print(f"found existing app in {app_path}")

                    # Change to app_dir
                    os.chdir(app_path)

                    # Pull
                    print(f"pulling updates from {self.source}")
                    repo = Repo(app_path)
                    assert repo.__class__ is Repo

                    repo.remotes.origin.pull()

                    # Return to previous directory
                    os.chdir(cwd)
                else:
                    print(f"cloning from {self.source}")
                    repo = Repo.clone_from(self.source, app_path)
                assert repo.__class__ is Repo

                # Set app path
                self.path = app_path

                # Set app name from git remote
                remote_url = repo.remotes[0].config_reader.get(
                    "url"
                )  # e.g. 'https://github.com/abc123/MyRepo.git'
                self.name = os.path.splitext(os.path.basename(remote_url))[0]  # 'MyRepo'
            except Exception as e:
                raise CannotInstallApp(f"Failed to install app from {self.source}: {e}")

        # Save app to user config
        try:
            custom_config = {"apps": {}}
            custom_config["apps"][self.name] = {
                "path": self.path,
                "params": {},
            }

            if self.source:
                custom_config["apps"][self.name]["source"] = self.source
            else:
                custom_config["apps"][self.name]["source"] = self.path

            self.config.write(custom_config)
            if self.config.verbose > 0:
                typer.secho(
                    f"Saving new config to {self.config.config_path}",
                    err=False,
                    fg=typer.colors.BRIGHT_BLACK,
                )
        except Exception as e:
            raise CannotInstallApp(f"Cannot save config: {e}")

        # Install the app
        try:
            install_command = [
                "docker-compose",
                "-p",
                self.name,
            ]

            if self.config.verbose:
                install_command.append("--verbose")

            env_file = os.path.join(self.path, ".env")
            if os.path.exists(env_file):
                install_command.append("--env-file")
                install_command.append(str(env_file))

            # Check existence of compose files
            compose_file = os.path.join(self.path, self.compose_file)
            app_config = {}
            if os.path.exists(compose_file):
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

            # Augment
            os.environ["BUILD_DATE"] = datetime.datetime.utcnow().isoformat()
            # os.environ["BUILD_VERSION"]
            # BUILD_VERSION
            # VCS_REF

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
                    if self.config.verbose:
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
