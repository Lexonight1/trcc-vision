"""Centralized logging setup — rotating file + console handlers.

Call setup_logging() once from each adapter entry point (CLI, GUI, API).
Every module uses: log = logging.getLogger(__name__)
"""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

LOG_FORMAT = "%(asctime)s [%(levelname)-8s] %(name)s: %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
LOG_FILE_NAME = "trcc-vision.log"
LOG_MAX_BYTES = 5 * 1024 * 1024  # 5 MB
LOG_BACKUP_COUNT = 3

_initialized = False

log = logging.getLogger(__name__)


def setup_logging(
    *,
    console_level: int = logging.INFO,
    file_level: int = logging.DEBUG,
    log_file: Path | None = None,
    enable_console: bool = True,
    enable_file: bool = True,
) -> None:
    """Configure the root logger with console and/or rotating file handlers.

    Args:
        console_level: Logging level for console output.
        file_level: Logging level for file output.
        log_file: Override log file path. Defaults to platform log_dir()/trcc-vision.log.
        enable_console: Whether to add a console (stderr) handler.
        enable_file: Whether to add a rotating file handler.
    """
    global _initialized  # noqa: PLW0603
    if _initialized:
        log.debug("Logging already initialized, skipping")
        return

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)  # capture everything, handlers filter

    formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)

    if enable_console:
        console = logging.StreamHandler(sys.stderr)
        console.setLevel(console_level)
        console.setFormatter(formatter)
        root.addHandler(console)

    if enable_file:
        if log_file is None:
            from trcc_vision.infrastructure.platform import log_dir
            log_file = log_dir() / LOG_FILE_NAME

        log_file.parent.mkdir(parents=True, exist_ok=True)

        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=LOG_MAX_BYTES,
            backupCount=LOG_BACKUP_COUNT,
            encoding="utf-8",
        )
        file_handler.setLevel(file_level)
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)

    _initialized = True
    log.debug(
        "Logging initialized: console=%s(%s), file=%s(%s)",
        enable_console,
        logging.getLevelName(console_level),
        enable_file,
        log_file,
    )


def reset_logging() -> None:
    """Remove all handlers from root logger. Used in tests."""
    global _initialized  # noqa: PLW0603
    root = logging.getLogger()
    for handler in root.handlers[:]:
        root.removeHandler(handler)
        handler.close()
    _initialized = False
