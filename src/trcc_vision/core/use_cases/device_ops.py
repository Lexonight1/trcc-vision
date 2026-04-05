"""Device use cases — detect, connect, disconnect, status."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from trcc_vision.core.events import DeviceConnected, DeviceDisconnected

if TYPE_CHECKING:
    from trcc_vision.core.events import EventBus
    from trcc_vision.core.models import DeviceInfo
    from trcc_vision.services.device import DeviceService

log = logging.getLogger(__name__)


@dataclass
class DeviceStatus:
    """Result of GetDeviceStatus."""

    connected: bool
    device: DeviceInfo | None = None


class DetectDevices:
    """Scan for connected TR-VISION devices."""

    def __init__(self, device_service: DeviceService) -> None:
        self._svc = device_service

    def execute(self) -> list[DeviceInfo]:
        log.info("Detecting devices...")
        devices = self._svc.detect()
        log.info("Found %d device(s)", len(devices))
        return devices


class ConnectDevice:
    """Establish connection to a specific device."""

    def __init__(self, device_service: DeviceService, event_bus: EventBus) -> None:
        self._svc = device_service
        self._bus = event_bus

    def execute(self, device: DeviceInfo) -> bool:
        log.info("Connecting to %s (%s)...", device.name, device.address)
        try:
            self._svc.select(device)
            self._bus.publish(DeviceConnected(device=device))
            log.info("Connected to %s", device.name)
            return True
        except Exception:
            log.exception("Failed to connect to %s", device.name)
            return False


class DisconnectDevice:
    """Disconnect from current device."""

    def __init__(self, device_service: DeviceService, event_bus: EventBus) -> None:
        self._svc = device_service
        self._bus = event_bus

    def execute(self) -> bool:
        log.info("Disconnecting from device...")
        try:
            self._svc.disconnect()
            self._bus.publish(DeviceDisconnected())
            log.info("Disconnected")
            return True
        except Exception:
            log.exception("Failed to disconnect")
            return False


class GetDeviceStatus:
    """Check current device connection state."""

    def __init__(self, device_service: DeviceService) -> None:
        self._svc = device_service

    def execute(self) -> DeviceStatus:
        device = self._svc.selected
        connected = device is not None
        log.debug("Device status: connected=%s, device=%s", connected, device)
        return DeviceStatus(connected=connected, device=device)
