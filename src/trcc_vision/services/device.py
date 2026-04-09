"""Device service — detect, connect, and communicate with TR-VISION hardware."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from trcc_vision.core.enums import ConnectionType
from trcc_vision.core.models import DeviceInfo

if TYPE_CHECKING:
    from trcc_vision.core.ports import ConfigPort, DevicePort
    from trcc_vision.protocols.adb import ADBPort

log = logging.getLogger(__name__)

_CFG_LAST_DEVICE = "last_device_address"
_CFG_LAST_CONN = "last_device_connection"


class DeviceService:
    """Orchestrates device detection, selection, and frame sending."""

    def __init__(
        self,
        device_port: DevicePort,
        adb: ADBPort | None = None,
        config: ConfigPort | None = None,
    ) -> None:
        self._port = device_port
        self._adb = adb
        self._config = config
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
        self._save_last_device(device)
        log.info("Device connected: %s", device.name)

    def disconnect(self) -> None:
        """Disconnect from current device."""
        if self._selected:
            self._port.disconnect()
            log.info("Disconnected from %s", self._selected.name)
            self._selected = None
            self._clear_last_device()
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

    def reconnect_last(self) -> bool:
        """Reconnect to the last known device from persisted config.

        Returns True if reconnection succeeded, False otherwise.
        """
        if self.is_connected:
            return True
        if not self._config:
            return False

        address = self._config.get(_CFG_LAST_DEVICE)
        conn_type = self._config.get(_CFG_LAST_CONN, ConnectionType.ADB.value)
        if not address or not isinstance(address, str):
            return False

        log.info("Reconnecting to last device: %s", address)
        device = DeviceInfo(
            name=f"TR-VISION ({address})",
            connection=ConnectionType(conn_type),
            address=address,
        )
        try:
            self.select(device)
            return True
        except Exception:
            log.warning("Failed to reconnect to last device: %s", address)
            self._clear_last_device()
            return False

    def _save_last_device(self, device: DeviceInfo) -> None:
        """Persist last connected device address to config."""
        if self._config:
            self._config.set(_CFG_LAST_DEVICE, device.address)
            self._config.set(_CFG_LAST_CONN, device.connection.value)
            log.debug("Saved last device: %s", device.address)

    def _clear_last_device(self) -> None:
        """Remove last device from config."""
        if self._config:
            self._config.set(_CFG_LAST_DEVICE, "")
            self._config.set(_CFG_LAST_CONN, "")
            log.debug("Cleared last device from config")

    def push_file(self, local_path: str, remote_path: str) -> bool:
        """Push a file to the device via ADB."""
        if not self._adb:
            log.error("No ADB port for file push")
            return False
        return self._adb.push(local_path, remote_path)
