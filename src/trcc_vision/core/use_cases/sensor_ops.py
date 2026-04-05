"""Sensor use cases — read hardware sensors."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from trcc_vision.core.events import SensorUpdated

if TYPE_CHECKING:
    from trcc_vision.core.enums import SensorType
    from trcc_vision.core.events import EventBus
    from trcc_vision.core.models import SensorReading
    from trcc_vision.services.sensor import SensorService

log = logging.getLogger(__name__)


class ReadAllSensors:
    """Read all available hardware sensors and publish update."""

    def __init__(self, sensor_service: SensorService, event_bus: EventBus) -> None:
        self._svc = sensor_service
        self._bus = event_bus

    def execute(self) -> list[SensorReading]:
        log.debug("Reading all sensors...")
        readings = self._svc.read_all()
        log.info("Read %d sensor(s)", len(readings))
        self._bus.publish(SensorUpdated(readings=readings))
        return readings


class ReadSensor:
    """Read a single sensor by type."""

    def __init__(self, sensor_service: SensorService) -> None:
        self._svc = sensor_service

    def execute(self, sensor_type: SensorType) -> SensorReading | None:
        log.debug("Reading sensor type=%s", sensor_type)
        reading = self._svc.get(sensor_type)
        if reading:
            log.debug("Sensor %s: %.1f %s", reading.label, reading.value, reading.unit)
        else:
            log.warning("No reading for sensor type=%s", sensor_type)
        return reading
