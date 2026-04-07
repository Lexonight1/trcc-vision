"""ADB protocol — ABC, base adapter, and shared types.

Defines the platform-agnostic ADB interface (ADBPort) and a base
implementation (_BaseADBAdapter) that handles command execution.
Platform-specific adapters override binary resolution and subprocess
kwargs.

Derived from decompiled ADBHelper.cs.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger(__name__)

ADB_TIMEOUT = 10  # seconds per command


@dataclass
class ADBDevice:
    """A device visible to ADB."""

    serial: str  # e.g. "192.168.1.100:5555" or "ABCD1234"
    state: str   # "device", "offline", "unauthorized"


class ADBError(Exception):
    """Raised when an ADB command fails."""


# ── ABC ────────────────────────────────────────────────────────────────


class ADBPort(ABC):
    """Platform-agnostic ADB operations.

    Each platform provides its own adapter implementing this interface.
    Use ``create_adb_port()`` from ``adb_factory`` to get the right one.
    """

    @abstractmethod
    def devices(self) -> list[ADBDevice]:
        """List connected ADB devices."""

    @abstractmethod
    def connect(self, host: str, port: int = 5555) -> bool:
        """Connect to a network ADB device."""

    @abstractmethod
    def disconnect(self, host: str | None = None, port: int = 5555) -> None:
        """Disconnect from an ADB device (or all if host is None)."""

    @abstractmethod
    def push(self, local_path: str, remote_path: str) -> bool:
        """Push a local file to the device."""

    @abstractmethod
    def shell(self, cmd: str, timeout: int = ADB_TIMEOUT) -> str:
        """Execute a shell command on the device."""

    @abstractmethod
    def forward(self, local_port: int, remote_port: int) -> bool:
        """Set up TCP port forwarding: local → device."""

    @abstractmethod
    def get_version(self) -> str | None:
        """Get the ADB binary version string."""

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the ADB binary is reachable."""


# ── Base Adapter ───────────────────────────────────────────────────────


class _BaseADBAdapter(ADBPort):
    """Common ADB logic — subclasses override ``_resolve_binary()``.

    Provides the full ADB command interface via subprocess. Platform
    adapters only need to specify where to find the binary and any
    extra subprocess kwargs (e.g. Windows console suppression).
    """

    def __init__(self, adb_path: str | None = None) -> None:
        if adb_path:
            self._adb = adb_path
        else:
            self._adb = str(self._resolve_binary())
        log.info("ADB binary: %s", self._adb)

    def _resolve_binary(self) -> Path:
        """Return the path to the ADB binary for this platform.

        Default: ``shutil.which("adb")`` or bare ``"adb"``.
        Platform adapters override this with platform-specific search.
        """
        found = shutil.which("adb")
        return Path(found) if found else Path("adb")

    def _extra_popen_kwargs(self) -> dict:
        """Platform-specific kwargs for ``subprocess.run``.

        Override on Windows to suppress console popups.
        """
        return {}

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
                **self._extra_popen_kwargs(),
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

    # ── ADBPort implementation ─────────────────────────────────────────

    def devices(self) -> list[ADBDevice]:
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
        if host:
            target = f"{host}:{port}"
            log.info("Disconnecting ADB device: %s", target)
            self._run("disconnect", target)
        else:
            log.info("Disconnecting all ADB devices")
            self._run("disconnect")

    def push(self, local_path: str, remote_path: str) -> bool:
        log.info("ADB push: %s → %s", local_path, remote_path)
        try:
            self._run("push", local_path, remote_path)
            log.info("Push complete: %s", remote_path)
            return True
        except ADBError:
            log.exception("Push failed: %s → %s", local_path, remote_path)
            return False

    def shell(self, cmd: str, timeout: int = ADB_TIMEOUT) -> str:
        log.debug("ADB shell: %s", cmd)
        return self._run("shell", cmd, timeout=timeout)

    def forward(self, local_port: int, remote_port: int) -> bool:
        log.info("ADB forward: tcp:%d → tcp:%d", local_port, remote_port)
        try:
            self._run("forward", f"tcp:{local_port}", f"tcp:{remote_port}")
            return True
        except ADBError:
            log.exception("Port forward failed")
            return False

    def get_version(self) -> str | None:
        try:
            return self._run("version").splitlines()[0]
        except ADBError:
            return None

    def is_available(self) -> bool:
        return shutil.which(self._adb) is not None


# ── Backwards-compatible alias ─────────────────────────────────────────

ADBProtocol = _BaseADBAdapter
