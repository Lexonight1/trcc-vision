"""Sensor factory — returns the correct SensorPort for the current platform.

Usage:
    port = create_sensor_port()
    readings = port.read_all()
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from trcc_vision.core.ports import SensorPort
from trcc_vision.infrastructure.platform import Platform, current_platform

if TYPE_CHECKING:
    from trcc_vision.core.models import SensorReading

log = logging.getLogger(__name__)


class NullSensorPort(SensorPort):
    """Fallback port that returns no readings. Used on unknown platforms."""

    def read_all(self) -> list[SensorReading]:
        log.debug("NullSensorPort.read_all() — no sensor backend available")
        return []

    def read_type(self, sensor_type: int) -> SensorReading | None:
        return None


def create_sensor_port() -> SensorPort:
    """Create the platform-appropriate SensorPort.

    Returns NullSensorPort if the platform is unsupported or if the
    backend fails to initialize.
    """
    platform = current_platform()
    log.info("Creating sensor port for platform: %s", platform.value)

    try:
        if platform == Platform.LINUX:
            from trcc_vision.infrastructure.sensors_linux import LinuxSensorPort
            return LinuxSensorPort()

        if platform == Platform.MACOS:
            from trcc_vision.infrastructure.sensors_macos import MacOSSensorPort
            return MacOSSensorPort()

        if platform == Platform.WINDOWS:
            from trcc_vision.infrastructure.sensors_windows import WindowsSensorPort
            return WindowsSensorPort()

        if platform == Platform.BSD:
            from trcc_vision.infrastructure.sensors_bsd import BSDSensorPort
            return BSDSensorPort()

    except Exception:
        log.exception("Failed to create sensor port for %s", platform.value)

    log.warning("No sensor backend for %s, using NullSensorPort", platform.value)
    return NullSensorPort()
