"""ADB adapter factory — returns the correct ADBPort for the current platform.

Usage:
    port = create_adb_port()
    devices = port.devices()
"""

from __future__ import annotations

import logging

from trcc_vision.infrastructure.platform import Platform, current_platform
from trcc_vision.protocols.adb import ADB_TIMEOUT, ADBDevice, ADBError, ADBPort

log = logging.getLogger(__name__)


class NullADBPort(ADBPort):
    """Fallback port that always reports ADB unavailable.

    Used on unknown platforms or when the real adapter fails to initialize.
    """

    def devices(self) -> list[ADBDevice]:
        log.debug("NullADBPort.devices() — no ADB backend available")
        return []

    def connect(self, host: str, port: int = 5555) -> bool:
        return False

    def disconnect(self, host: str | None = None, port: int = 5555) -> None:
        pass

    def push(self, local_path: str, remote_path: str) -> bool:
        return False

    def shell(self, cmd: str, timeout: int = ADB_TIMEOUT) -> str:
        raise ADBError("ADB not available on this platform")

    def forward(self, local_port: int, remote_port: int) -> bool:
        return False

    def get_version(self) -> str | None:
        return None

    def is_available(self) -> bool:
        return False


def create_adb_port() -> ADBPort:
    """Create the platform-appropriate ADBPort.

    Returns NullADBPort if the platform is unsupported or if the
    backend fails to initialize.
    """
    platform = current_platform()
    log.info("Creating ADB adapter for platform: %s", platform.value)

    try:
        if platform == Platform.LINUX:
            from trcc_vision.protocols.adb_linux import LinuxADBAdapter
            return LinuxADBAdapter()

        if platform == Platform.MACOS:
            from trcc_vision.protocols.adb_macos import MacOSADBAdapter
            return MacOSADBAdapter()

        if platform == Platform.WINDOWS:
            from trcc_vision.protocols.adb_windows import WindowsADBAdapter
            return WindowsADBAdapter()

        if platform == Platform.BSD:
            from trcc_vision.protocols.adb_bsd import BSDADBAdapter
            return BSDADBAdapter()

    except Exception:
        log.exception("Failed to create ADB adapter for %s", platform.value)

    log.warning("No ADB backend for %s, using NullADBPort", platform.value)
    return NullADBPort()
