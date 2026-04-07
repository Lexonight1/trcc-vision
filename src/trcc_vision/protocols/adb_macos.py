"""macOS ADB adapter — resolves ADB from Homebrew, Android SDK, or PATH."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

from trcc_vision.protocols.adb import _BaseADBAdapter

log = logging.getLogger(__name__)


class MacOSADBAdapter(_BaseADBAdapter):
    """ADB adapter for macOS.

    Search order:
    1. System PATH (Homebrew or manual install)
    2. Homebrew Apple Silicon: ``/opt/homebrew/bin/adb``
    3. Homebrew Intel: ``/usr/local/bin/adb``
    4. Android Studio SDK: ``~/Library/Android/sdk/platform-tools/adb``
    5. Bare ``adb`` fallback
    """

    def _resolve_binary(self) -> Path:
        # System PATH — covers Homebrew and manual installs
        found = shutil.which("adb")
        if found:
            log.debug("ADB found in PATH: %s", found)
            return Path(found)

        # Homebrew Apple Silicon
        brew_arm = Path("/opt/homebrew/bin/adb")
        if brew_arm.is_file():
            log.debug("ADB found at Homebrew (ARM): %s", brew_arm)
            return brew_arm

        # Homebrew Intel
        brew_x86 = Path("/usr/local/bin/adb")
        if brew_x86.is_file():
            log.debug("ADB found at Homebrew (x86): %s", brew_x86)
            return brew_x86

        # Android Studio SDK default location on macOS
        sdk_adb = Path.home() / "Library" / "Android" / "sdk" / "platform-tools" / "adb"
        if sdk_adb.is_file():
            log.debug("ADB found at Android SDK: %s", sdk_adb)
            return sdk_adb

        log.warning("ADB binary not found on macOS, using bare 'adb' fallback")
        return Path("adb")
