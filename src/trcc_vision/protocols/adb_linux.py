"""Linux ADB adapter — resolves ADB binary from system packages or Android SDK."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

from trcc_vision.protocols.adb import _BaseADBAdapter

log = logging.getLogger(__name__)


class LinuxADBAdapter(_BaseADBAdapter):
    """ADB adapter for Linux.

    Search order:
    1. System PATH (distro packages: ``apt install adb``, ``pacman -S android-tools``)
    2. Android SDK at ``~/Android/Sdk/platform-tools/adb``
    3. Bare ``adb`` fallback (lets subprocess raise on first use)
    """

    def _resolve_binary(self) -> Path:
        # System PATH — covers distro packages
        found = shutil.which("adb")
        if found:
            log.debug("ADB found in PATH: %s", found)
            return Path(found)

        # Android Studio SDK default location
        sdk_adb = Path.home() / "Android" / "Sdk" / "platform-tools" / "adb"
        if sdk_adb.is_file():
            log.debug("ADB found at Android SDK: %s", sdk_adb)
            return sdk_adb

        log.warning("ADB binary not found on Linux, using bare 'adb' fallback")
        return Path("adb")
