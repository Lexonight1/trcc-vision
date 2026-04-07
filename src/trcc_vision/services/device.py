"""Device service — detect, connect, and communicate with TR-VISION hardware."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from trcc_vision.core.enums import ConnectionType
from trcc_vision.core.models import DeviceInfo

if TYPE_CHECKING:
    from trcc_vision.core.ports import DevicePort
    from trcc_vision.protocols.adb import ADBPort

log = logging.getLogger(__name__)


class DeviceService:
    """Orchestrates device detection, selection, and frame sending."""

    def __init__(self, device_port: DevicePort, adb: ADBPort | None = None) -> None:
        self._port = device_port
        self._adb = adb
        self._selected: DeviceInfo | None = None

    def detect(self) -> list[DeviceInfo]:
        """Scan for connected TR-VISION devices via ADB."""
        log.info("Scanning for TR-VISION devices...")

        if not self._adb:
            log.warning("No ADB port available for device detection")
            return []

        if not self._adb.is_available():
            log.warning("ADB binary not found — cannot scan for devices")
            return []

        try:
            adb_devices = self._adb.devices()
        except Exception:
            log.exception("ADB device scan failed")
            return []

        devices: list[DeviceInfo] = []
        for dev in adb_devices:
            if dev.state != "device":
                log.debug("Skipping ADB device %s (state=%s)", dev.serial, dev.state)
                continue
            devices.append(DeviceInfo(
                name=f"TR-VISION ({dev.serial})",
                connection=ConnectionType.ADB,
                address=dev.serial,
            ))

        log.info("Found %d TR-VISION device(s)", len(devices))
        return devices

    def select(self, device: DeviceInfo) -> None:
        """Select a device and establish connection."""
        log.info("Connecting to device: %s (%s)", device.name, device.address)
        self._port.connect(device)
        self._selected = device
        log.info("Device connected: %s", device.name)

    def disconnect(self) -> None:
        """Disconnect from current device."""
        if self._selected:
            self._port.disconnect()
            log.info("Disconnected from %s", self._selected.name)
            self._selected = None
        else:
            log.debug("No device to disconnect")

    @property
    def selected(self) -> DeviceInfo | None:
        return self._selected

    @property
    def is_connected(self) -> bool:
        return self._selected is not None and self._port.is_connected()

    def send_frame(self, data: bytes, width: int, height: int) -> None:
        """Send an LCD frame to the selected device."""
        if not self._selected:
            raise RuntimeError("No device selected")
        self._port.send_frame(data, width, height)
        log.debug("Frame sent: %d bytes (%dx%d)", len(data), width, height)

    def send_command(self, cmd: bytes) -> bytes:
        """Send a raw command to the selected device."""
        if not self._selected:
            raise RuntimeError("No device selected")
        return self._port.send_command(cmd)

    def push_file(self, local_path: str, remote_path: str) -> bool:
        """Push a file to the device via ADB."""
        if not self._adb:
            log.error("No ADB port for file push")
            return False
        return self._adb.push(local_path, remote_path)
