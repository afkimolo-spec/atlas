from __future__ import annotations

import logging
from pathlib import Path

from atlas.config.loader import load_logging

_config = load_logging()

LOG_ROOT = Path("/home/administrator/workspace/atlas")


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    logger.setLevel(getattr(logging, _config.level))

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

    console = logging.StreamHandler()
    console.setFormatter(formatter)

    logfile = LOG_ROOT / _config.files.atlas

    logfile.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    file_handler = logging.FileHandler(
        logfile,
        encoding="utf-8",
    )

    file_handler.setFormatter(formatter)

    logger.addHandler(console)
    logger.addHandler(file_handler)

    logger.propagate = False

    return logger
