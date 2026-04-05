"""BSD sensor backend — reads via sysctl.

Supports FreeBSD, OpenBSD, and NetBSD. Uses sysctl for CPU temp, load,
and RAM. Network via netstat. Graceful degradation — returns what's available.

FreeBSD: sysctl dev.cpu.0.temperature, hw.physmem, vm.stats.vm.*
OpenBSD: sysctl hw.sensors.cpu0.temp0, hw.physmem
NetBSD:  sysctl hw.physmem (limited sensor support)
"""

from __future__ import annotations

import logging
import re
import subprocess
import time

from trcc_vision.core.enums import SensorType
from trcc_vision.core.models import SensorReading
from trcc_vision.core.ports import SensorPort

log = logging.getLogger(__name__)

_CMD_TIMEOUT = 5


def _sysctl(key: str) -> str | None:
    """Read a sysctl value."""
    try:
        result = subprocess.run(
            ["sysctl", "-n", key],
            capture_output=True, text=True, timeout=_CMD_TIMEOUT,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return None


def _read_cpu_temp() -> SensorReading | None:
    """Read CPU temperature via sysctl (FreeBSD/OpenBSD paths)."""
    # FreeBSD: dev.cpu.0.temperature → "55.0C"
    raw = _sysctl("dev.cpu.0.temperature")
    if raw:
        match = re.search(r"([\d.]+)", raw)
        if match:
            return SensorReading(
                SensorType.CPU_TEMP, "CPU Temperature",
                float(match.group(1)), "°C", time.time(),
            )

    # OpenBSD: hw.sensors.cpu0.temp0 → "55.00 degC"
    raw = _sysctl("hw.sensors.cpu0.temp0")
    if raw:
        match = re.search(r"([\d.]+)", raw)
        if match:
            return SensorReading(
                SensorType.CPU_TEMP, "CPU Temperature",
                float(match.group(1)), "°C", time.time(),
            )

    log.debug("No CPU temperature source on this BSD variant")
    return None


def _read_cpu_load() -> SensorReading | None:
    """Read CPU load from sysctl vm.loadavg."""
    raw = _sysctl("vm.loadavg")
    if raw is None:
        return None
    # FreeBSD: "{ 0.50 0.60 0.70 }" or just "0.50 0.60 0.70"
    match = re.search(r"([\d.]+)", raw)
    if not match:
        return None
    ncpu_raw = _sysctl("hw.ncpu")
    ncpu = int(ncpu_raw) if ncpu_raw else 1
    load = float(match.group(1)) / ncpu * 100.0
    return SensorReading(
        SensorType.CPU_LOAD, "CPU Load",
        round(min(load, 100.0), 1), "%", time.time(),
    )


def _read_ram() -> list[SensorReading]:
    """Read RAM via sysctl hw.physmem."""
    readings: list[SensorReading] = []
    raw = _sysctl("hw.physmem")
    if raw is None:
        return readings

    now = time.time()
    try:
        total_bytes = int(raw)
    except ValueError:
        return readings

    total_gb = total_bytes / (1024 ** 3)
    readings.append(SensorReading(
        SensorType.RAM_SIZE, "RAM Total",
        round(total_gb, 1), "GB", now,
    ))

    # FreeBSD: vm.stats.vm.v_free_count * hw.pagesize
    free_count_raw = _sysctl("vm.stats.vm.v_free_count")
    pagesize_raw = _sysctl("hw.pagesize")
    if free_count_raw and pagesize_raw:
        try:
            free_bytes = int(free_count_raw) * int(pagesize_raw)
            used_bytes = total_bytes - free_bytes
            readings.extend([
                SensorReading(SensorType.RAM_USED, "RAM Used",
                              round(used_bytes / (1024 ** 3), 1), "GB", now),
                SensorReading(SensorType.RAM_AVAILABLE, "RAM Available",
                              round(free_bytes / (1024 ** 3), 1), "GB", now),
                SensorReading(SensorType.RAM_USAGE_RATE, "RAM Usage",
                              round(100.0 * used_bytes / total_bytes, 1), "%", now),
            ])
        except ValueError:
            pass

    return readings


class BSDSensorPort(SensorPort):
    """SensorPort for FreeBSD/OpenBSD/NetBSD using sysctl."""

    def read_all(self) -> list[SensorReading]:
        log.debug("Reading all BSD sensors...")
        readings: list[SensorReading] = []

        cpu_temp = _read_cpu_temp()
        if cpu_temp:
            readings.append(cpu_temp)

        cpu_load = _read_cpu_load()
        if cpu_load:
            readings.append(cpu_load)

        readings.extend(_read_ram())

        log.debug("BSD sensors: %d readings", len(readings))
        return readings

    def read_type(self, sensor_type: int) -> SensorReading | None:
        for reading in self.read_all():
            if reading.sensor_type == sensor_type:
                return reading
        return None
