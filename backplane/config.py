import os
from pathlib import Path, PosixPath
import anyconfig
import sys
import json
from json import JSONEncoder
from .errors import ConfigNotFound
import typer


class CustomEncoder(JSONEncoder):
    def default(self, o):
        if isinstance(o, PosixPath):
            return str(o)


class Config:
    def __init__(self, config_path: Path = None):
        self.config_dir: Path = Path(
            os.getenv(
                "BACKPLANE_CONFIG_DIR",
                os.path.join(os.getenv("HOME", Path.home()), ".backplane"),
            )
        )
        self.default_context: str = "default"
        self.active_context: str = "default"
        self.mail: str = None
        self.default_services: list = ["traefik", "portainer", "backplane"]
        self.apps: dict = {}
        self.appstore_url: str = "https://github.com/backplane-apps"
        self.verbose: bool = False
        self.user: str = "admin"
        self.password: str = "backplane"
        self.password_hash: str = (
            "$2y$05$G3uDxpEVTu4J.08zkpN2Ru0r1Xaoz1V88LF47EF97BAmjlvsN3Jj6"
        )
        self.template_url: str = "https://raw.githubusercontent.com/wearep3r/backplane/master/backplane-templates.json"
        self.ssh_public_key: str = None
        self.ssh_public_key_file: Path = Path(f"{os.getenv('HOME')}/.ssh/id_rsa.pub")
        self.https: bool = False
        self.domain: str = "127-0-0-1.ns0.co"
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
        self.app_dir: Path = Path(self.active_context_dir / "apps")

        self.load()

    def serialize(self, data=None):
        if not data:
            return CustomEncoder().encode(dict(self.__dict__))
        else:
            return CustomEncoder().encode(dict(data))

    def toJSON(self, data=None):
        if not data:
            return self.serialize()
        else:
            return self.serialize(data)

    def toDict(self, data=None):
        if not data:
            return json.loads(self.serialize())
        else:
            return json.loads(self.serialize(data))

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

    def write(self, custom_config: dict = None):
        # Note: this is only dealing with user config
        if not os.path.exists(self.config_path):
            # Create an empty config
            with open(self.config_path, "a"):
                os.utime(self.config_path, None)
        try:
            if not custom_config:
                backplane_config = anyconfig.loads(
                    json.dumps(self.toDict()), ac_parser="json"
                )
            else:
                # Only write user config, not the whole thing
                user_config = anyconfig.load([str(self.config_path)])
                anyconfig.merge(user_config, self.toDict(custom_config))
                backplane_config = user_config
            # anyconfig.merge(backplane_config, config)
            # if os.path.exists(config_path):

            # Open ~/.backplane/contexts/default/backplane.yml
            # Save config as yml

            with open(self.config_path, "w+") as writer:
                writer.write(anyconfig.dumps(backplane_config, ac_parser="yaml"))

            return backplane_config
        except OSError as e:
            raise ConfigNotFound(e)
