from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

from atlas.config.settings import (
    Logging,
    Models,
    Security,
    Workspace,
)


DEFAULT_ROOT = (
    "/home/administrator/workspace/atlas"
)


PROJECT_ROOT = Path(
    os.getenv(
        "ATLAS_ROOT",
        DEFAULT_ROOT,
    )
).expanduser().resolve()


CONFIG_DIR = Path(
    os.getenv(
        "ATLAS_CONFIG_DIR",
        str(PROJECT_ROOT / "configs"),
    )
).expanduser().resolve()


def load_yaml(
    filename: str,
) -> dict[str, Any]:
    filename = filename.strip()

    if not filename:
        raise ValueError(
            "Configuration filename cannot be empty."
        )

    path = (
        CONFIG_DIR / filename
    ).resolve()

    if (
        path != CONFIG_DIR
        and CONFIG_DIR not in path.parents
    ):
        raise ValueError(
            "Configuration path escapes config directory: "
            f"{filename}"
        )

    if not path.exists():
        raise FileNotFoundError(
            f"Configuration file not found: {path}"
        )

    if not path.is_file():
        raise FileNotFoundError(
            f"Configuration path is not a file: {path}"
        )

    with path.open(
        "r",
        encoding="utf-8",
    ) as file:
        data = yaml.safe_load(file)

    if not isinstance(data, dict):
        raise ValueError(
            f"Configuration root must be a mapping: {path}"
        )

    return data


def _section(
    filename: str,
    section: str,
) -> dict[str, Any]:
    data = load_yaml(filename)

    value = data.get(section)

    if not isinstance(value, dict):
        raise ValueError(
            f"Configuration '{filename}' must contain "
            f"a '{section}' mapping."
        )

    return value


MODELS = Models(
    **_section(
        "models.yaml",
        "models",
    )
)

WORKSPACE = Workspace(
    **_section(
        "workspace.yaml",
        "workspace",
    )
)

LOGGING = Logging(
    **_section(
        "logging.yaml",
        "logging",
    )
)

SECURITY = Security(
    **_section(
        "security.yaml",
        "security",
    )
)


def load_models() -> Models:
    return MODELS


def load_workspace() -> Workspace:
    return WORKSPACE


def load_logging() -> Logging:
    return LOGGING


def load_security() -> Security:
    return SECURITY
