"""BSD ADB adapter — resolves ADB from ports/packages or PATH."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

from trcc_vision.protocols.adb import _BaseADBAdapter

log = logging.getLogger(__name__)


class BSDADBAdapter(_BaseADBAdapter):
    """ADB adapter for FreeBSD, OpenBSD, and NetBSD.

    Search order:
    1. System PATH (ports/packages)
    2. ``/usr/local/bin/adb`` (FreeBSD ports default)
    3. Bare ``adb`` fallback
    """

    def _resolve_binary(self) -> Path:
        # System PATH — covers ports/pkg installs
        found = shutil.which("adb")
        if found:
            log.debug("ADB found in PATH: %s", found)
            return Path(found)

        # FreeBSD ports default
        ports_adb = Path("/usr/local/bin/adb")
        if ports_adb.is_file():
            log.debug("ADB found at ports path: %s", ports_adb)
            return ports_adb

        log.warning("ADB binary not found on BSD, using bare 'adb' fallback")
        return Path("adb")
