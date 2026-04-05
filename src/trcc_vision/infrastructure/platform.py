"""Platform detection and cross-platform path resolution.

Supported platforms:
- Linux (all non-EOL distros)
- macOS (10.15+)
- Windows (10+)
- FreeBSD / OpenBSD / NetBSD

Linux/BSD: ~/.trcc-vision/ (single dot-directory, like trcc-linux uses ~/.trcc/)
macOS: ~/Library/Application Support/trcc-vision/
Windows: %APPDATA%/trcc-vision/
"""

from __future__ import annotations

import logging
import os
import sys
from enum import Enum
from pathlib import Path

log = logging.getLogger(__name__)

_APP_DIR_NAME = ".trcc-vision"
_APP_NAME = "trcc-vision"


class Platform(Enum):
    LINUX = "linux"
    MACOS = "macos"
    WINDOWS = "windows"
    BSD = "bsd"
    UNKNOWN = "unknown"


def current_platform() -> Platform:
    """Detect the current operating system."""
    p = sys.platform
    if p.startswith("linux"):
        result = Platform.LINUX
    elif p == "darwin":
        result = Platform.MACOS
    elif p == "win32":
        result = Platform.WINDOWS
    elif "bsd" in p:
        result = Platform.BSD
    else:
        result = Platform.UNKNOWN
    log.debug("Detected platform: %s (sys.platform=%s)", result.value, p)
    return result


def _home_dot_dir() -> Path:
    """~/.trcc-vision/ — single directory for Linux/BSD."""
    return Path.home() / _APP_DIR_NAME


def config_dir() -> Path:
    """User config directory."""
    platform = current_platform()

    if platform == Platform.WINDOWS:
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        return base / _APP_NAME
    if platform == Platform.MACOS:
        return Path.home() / "Library" / "Application Support" / _APP_NAME

    # Linux, BSD — ~/.trcc-vision/
    return _home_dot_dir()


def data_dir() -> Path:
    """User data directory (themes, downloads)."""
    platform = current_platform()

    if platform == Platform.WINDOWS:
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        return base / _APP_NAME
    if platform == Platform.MACOS:
        return Path.home() / "Library" / "Application Support" / _APP_NAME

    return _home_dot_dir() / "data"


def cache_dir() -> Path:
    """User cache directory."""
    platform = current_platform()

    if platform == Platform.WINDOWS:
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        return base / _APP_NAME / "cache"
    if platform == Platform.MACOS:
        return Path.home() / "Library" / "Caches" / _APP_NAME

    return _home_dot_dir() / "cache"


def log_dir() -> Path:
    """Log file directory."""
    platform = current_platform()

    if platform == Platform.WINDOWS:
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        return base / _APP_NAME / "logs"
    if platform == Platform.MACOS:
        return Path.home() / "Library" / "Logs" / _APP_NAME

    return _home_dot_dir() / "logs"
