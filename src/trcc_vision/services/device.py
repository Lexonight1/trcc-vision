"""Device service — detect, connect, and communicate with TR-VISION hardware."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trcc_vision.core.models import DeviceInfo
    from trcc_vision.core.ports import DevicePort

log = logging.getLogger(__name__)


class DeviceService:
    """Orchestrates device detection, selection, and frame sending."""

    def __init__(self, device_port: DevicePort) -> None:
        self._port = device_port
        self._selected: DeviceInfo | None = None

    def detect(self) -> list[DeviceInfo]:
        """Scan for connected TR-VISION devices."""
        log.debug("detect() called")
        # TODO: implement ADB/TCP/USB scanning via port
        log.info("Scanning for TR-VISION devices...")
        devices: list[DeviceInfo] = []
        log.info("Found %d device(s)", len(devices))
        return devices

    def select(self, device: DeviceInfo) -> None:
        """Select a device for communication."""
        log.debug("select() called: device=%s addr=%s", device.name, device.address)
        self._port.connect(device)
        self._selected = device
        log.info("Selected device: %s (%s)", device.name, device.address)

    def disconnect(self) -> None:
        """Disconnect from current device."""
        log.debug("disconnect() called: selected=%s", self._selected)
        if self._selected:
            self._port.disconnect()
            log.info("Disconnected from %s", self._selected.name)
            self._selected = None
        else:
            log.debug("No device to disconnect")

    @property
    def selected(self) -> DeviceInfo | None:
        return self._selected

    def send_frame(self, data: bytes, width: int, height: int) -> None:
        """Send an LCD frame to the selected device."""
        log.debug("send_frame() called: %d bytes, %dx%d", len(data), width, height)
        if not self._selected:
            log.error("send_frame() failed: no device selected")
            raise RuntimeError("No device selected")
        self._port.send_frame(data, width, height)
        log.debug("send_frame() completed")
