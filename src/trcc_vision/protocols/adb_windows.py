"""Windows ADB adapter — bundled binary, console suppression, SDK fallback."""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
from pathlib import Path

from trcc_vision.protocols.adb import _BaseADBAdapter

log = logging.getLogger(__name__)

# Bundled ADB lives alongside the package assets
_BUNDLED_ADB_DIR = Path(__file__).resolve().parent.parent / "assets" / "adb"


class WindowsADBAdapter(_BaseADBAdapter):
    """ADB adapter for Windows.

    Search order:
    1. Bundled ``assets/adb/adb.exe`` (ships with the app, includes DLLs)
    2. System PATH (user-installed platform-tools)
    3. Android SDK: ``%LOCALAPPDATA%\\Android\\Sdk\\platform-tools\\adb.exe``
    4. Bare ``adb`` fallback
    """

    def _resolve_binary(self) -> Path:
        # Bundled binary (matches C# app: assets/adb/adb.exe + DLLs)
        bundled = _BUNDLED_ADB_DIR / "adb.exe"
        if bundled.is_file():
            log.debug("ADB found bundled: %s", bundled)
            return bundled

        # System PATH
        found = shutil.which("adb.exe") or shutil.which("adb")
        if found:
            log.debug("ADB found in PATH: %s", found)
            return Path(found)

        # Android SDK default location on Windows
        local_app_data = os.environ.get("LOCALAPPDATA", "")
        if local_app_data:
            sdk_adb = Path(local_app_data) / "Android" / "Sdk" / "platform-tools" / "adb.exe"
            if sdk_adb.is_file():
                log.debug("ADB found at Android SDK: %s", sdk_adb)
                return sdk_adb

        log.warning("ADB binary not found on Windows, using bare 'adb' fallback")
        return Path("adb")

    def _extra_popen_kwargs(self) -> dict:
        """Suppress console window popup on Windows."""
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
        return {"startupinfo": startupinfo}
