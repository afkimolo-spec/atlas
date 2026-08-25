from pathlib import Path

import yaml

from atlas.config.settings import Logging
from atlas.config.settings import Models
from atlas.config.settings import Security
from atlas.config.settings import Workspace


CONFIG_DIR = Path("/home/administrator/workspace/atlas/configs")


def load_yaml(filename: str) -> dict:
    with open(CONFIG_DIR / filename, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


MODELS = Models(**load_yaml("models.yaml")["models"])
WORKSPACE = Workspace(**load_yaml("workspace.yaml")["workspace"])
LOGGING = Logging(**load_yaml("logging.yaml")["logging"])
SECURITY = Security(**load_yaml("security.yaml")["security"])


def load_models() -> Models:
    return MODELS


def load_workspace() -> Workspace:
    return WORKSPACE


def load_logging() -> Logging:
    return LOGGING


def load_security() -> Security:
    return SECURITY
