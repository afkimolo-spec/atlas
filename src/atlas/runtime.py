from __future__ import annotations

import os
from pathlib import Path


DEFAULT_ROOT = (
    "/home/administrator/workspace/atlas"
)


ROOT = Path(
    os.getenv(
        "ATLAS_ROOT",
        DEFAULT_ROOT,
    )
).expanduser().resolve()


CONFIG_DIR = Path(
    os.getenv(
        "ATLAS_CONFIG_DIR",
        str(ROOT / "configs"),
    )
).expanduser().resolve()


MEMORY_DIR = (
    ROOT
    / ".ai"
    / "memory"
)


DATABASE = (
    MEMORY_DIR
    / "db"
    / "atlas.db"
)


LOG_ROOT = (
    ROOT
    / "logs"
)
