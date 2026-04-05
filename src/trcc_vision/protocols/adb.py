"""ADB protocol wrapper — cross-platform adb CLI interface.

Wraps the `adb` binary for device discovery, connection, file push, shell
commands, and port forwarding. Every command is logged at DEBUG with full
stdout/stderr capture.

Derived from decompiled ADBHelper.cs.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
from dataclasses import dataclass

log = logging.getLogger(__name__)

ADB_TIMEOUT = 10  # seconds per command


@dataclass
class ADBDevice:
    """A device visible to ADB."""

    serial: str  # e.g. "192.168.1.100:5555" or "ABCD1234"
    state: str   # "device", "offline", "unauthorized"


class ADBError(Exception):
    """Raised when an ADB command fails."""


class ADBProtocol:
    """Cross-platform wrapper around the `adb` CLI binary.

    Usage:
        adb = ADBProtocol()
        devices = adb.devices()
        adb.connect("192.168.1.100", 5555)
        adb.push("/tmp/image.png", "/sdcard/theme/00.png")
        output = adb.shell("getprop ro.build.version.release")
    """

    def __init__(self, adb_path: str | None = None) -> None:
        self._adb = adb_path or shutil.which("adb") or "adb"
        log.info("ADB binary: %s", self._adb)

    def _run(self, *args: str, timeout: int = ADB_TIMEOUT) -> str:
        """Execute an ADB command and return stdout.

        Raises ADBError on non-zero exit code.
        """
        cmd = [self._adb, *args]
        log.debug("ADB exec: %s", " ".join(cmd))
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except FileNotFoundError:
            log.error("ADB binary not found: %s", self._adb)
            raise ADBError(f"adb not found at {self._adb}") from None
        except subprocess.TimeoutExpired:
            log.error("ADB timeout after %ds: %s", timeout, " ".join(cmd))
            raise ADBError(f"adb timed out after {timeout}s") from None

        if result.returncode != 0:
            stderr = result.stderr.strip()
            log.error("ADB failed (rc=%d): %s", result.returncode, stderr)
            raise ADBError(f"adb error: {stderr}")

        stdout = result.stdout.strip()
        log.debug("ADB stdout: %s", stdout[:200] if len(stdout) > 200 else stdout)
        return stdout

    def devices(self) -> list[ADBDevice]:
        """List connected ADB devices."""
        log.debug("Listing ADB devices...")
        output = self._run("devices")
        result: list[ADBDevice] = []
        for line in output.splitlines()[1:]:  # skip header
            parts = line.split()
            if len(parts) >= 2:
                result.append(ADBDevice(serial=parts[0], state=parts[1]))
        log.info("Found %d ADB device(s)", len(result))
        return result

    def connect(self, host: str, port: int = 5555) -> bool:
        """Connect to a network ADB device."""
        target = f"{host}:{port}"
        log.info("Connecting to ADB device: %s", target)
        try:
            output = self._run("connect", target)
            connected = "connected" in output.lower()
            if connected:
                log.info("ADB connected to %s", target)
            else:
                log.warning("ADB connect response: %s", output)
            return connected
        except ADBError:
            return False

    def disconnect(self, host: str | None = None, port: int = 5555) -> None:
        """Disconnect from an ADB device (or all if host is None)."""
        if host:
            target = f"{host}:{port}"
            log.info("Disconnecting ADB device: %s", target)
            self._run("disconnect", target)
        else:
            log.info("Disconnecting all ADB devices")
            self._run("disconnect")

    def push(self, local_path: str, remote_path: str) -> bool:
        """Push a local file to the device."""
        log.info("ADB push: %s → %s", local_path, remote_path)
        try:
            self._run("push", local_path, remote_path)
            log.info("Push complete: %s", remote_path)
            return True
        except ADBError:
            log.exception("Push failed: %s → %s", local_path, remote_path)
            return False

    def shell(self, cmd: str, timeout: int = ADB_TIMEOUT) -> str:
        """Execute a shell command on the device."""
        log.debug("ADB shell: %s", cmd)
        return self._run("shell", cmd, timeout=timeout)

    def forward(self, local_port: int, remote_port: int) -> bool:
        """Set up TCP port forwarding: local → device."""
        log.info("ADB forward: tcp:%d → tcp:%d", local_port, remote_port)
        try:
            self._run("forward", f"tcp:{local_port}", f"tcp:{remote_port}")
            return True
        except ADBError:
            log.exception("Port forward failed")
            return False

    def get_version(self) -> str | None:
        """Get the ADB binary version string."""
        try:
            return self._run("version").splitlines()[0]
        except ADBError:
            return None

    def is_available(self) -> bool:
        """Check if the ADB binary is reachable."""
        return shutil.which(self._adb) is not None
