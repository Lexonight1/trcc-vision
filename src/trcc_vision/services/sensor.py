"""Sensor service — hardware sensor collection (CPU, GPU, RAM, disk, network)."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trcc_vision.core.models import SensorReading
    from trcc_vision.core.ports import SensorPort

log = logging.getLogger(__name__)


class SensorService:
    """Reads and caches hardware sensor values."""

    def __init__(self, sensor_port: SensorPort) -> None:
        self._port = sensor_port
        self._cache: dict[int, SensorReading] = {}

    def read_all(self) -> list[SensorReading]:
        """Read all sensors and update cache."""
        log.debug("read_all() called")
        readings = self._port.read_all()
        for r in readings:
            self._cache[r.sensor_type] = r
        log.debug("read_all() returned %d readings", len(readings))
        return readings

    def get(self, sensor_type: int) -> SensorReading | None:
        """Get a cached sensor reading, or read fresh if not cached."""
        log.debug("get() called: sensor_type=%d", sensor_type)
        if sensor_type in self._cache:
            log.debug("Cache hit for sensor_type=%d", sensor_type)
            return self._cache[sensor_type]
        reading = self._port.read_type(sensor_type)
        if reading:
            self._cache[sensor_type] = reading
            log.debug(
                "Fresh read for sensor_type=%d: %.1f %s",
                sensor_type, reading.value, reading.unit,
            )
        else:
            log.debug("No reading available for sensor_type=%d", sensor_type)
        return reading

    def clear_cache(self) -> None:
        """Clear sensor cache (forces fresh reads)."""
        log.debug("clear_cache() called, clearing %d entries", len(self._cache))
        self._cache.clear()
