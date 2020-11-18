import os
from pathlib import Path, PosixPath
import anyconfig
import sys
import json
from json import JSONEncoder
from .errors import ConfigNotFound


class CustomEncoder(JSONEncoder):
    def default(self, o):
        if isinstance(o, PosixPath):
            return str(o)


class Config:
    def __init__(self, config_path: Path = None):
        self.config_dir: Path = Path(
            os.getenv(
                "BACKPLANE_CONIG_DIR",
                os.path.join(os.getenv("HOME", Path.home()), ".backplane"),
            )
        )
        self.default_context: str = "default"
        self.active_context: str = "default"
        self.mail: str = None
        self.default_services: list = ["traefik", "portainer"]
        self.verbose: bool = False
        self.ssh_public_key: str = None
        self.ssh_public_key_file: Path = Path(f"{os.getenv('HOME')}/.ssh/id_rsa.pub")
        self.https: bool = False
        self.domain: str = "127-0-0-1.nip.io"
        self.contexts_dir: Path = os.getenv(
            "BACKPLANE_CONTEXTS_DIR", self.config_dir / "contexts"
        )
        self.default_context_dir: Path = self.contexts_dir / self.default_context
        self.contexts: dict = {
            "default": {
                "directory": os.getenv(
                    "BACKPLANE_DEFAULT_CONTEXT_DIR", self.default_context_dir
                )
            }
        }
        self.active_context_dir: Path = self.default_context_dir
        self.config_path: Path = (
            config_path if config_path else self.active_context_dir / "backplane.yml"
        )

        self.load()

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
