"""Windows sensor backend — uses psutil (required) + WMI (optional).

psutil covers: CPU load, RAM, disk, network.
WMI adds: CPU temperature, GPU data (when available).

psutil is cross-platform but is the most reliable option on Windows where
there's no sysfs/procfs equivalent. Install via: pip install trcc-vision[sensors]
"""

from __future__ import annotations

import logging
import time

from trcc_vision.core.enums import SensorType
from trcc_vision.core.models import SensorReading
from trcc_vision.core.ports import SensorPort

log = logging.getLogger(__name__)


def _try_import_psutil():  # noqa: ANN202
    """Import psutil, return None if not installed."""
    try:
        import psutil
        return psutil
    except ImportError:
        log.warning("psutil not installed — install with: pip install psutil")
        return None


def _try_import_wmi():  # noqa: ANN202
    """Import WMI, return None if not installed (Windows only)."""
    try:
        import wmi  # type: ignore[import-untyped]  # pyright: ignore[reportMissingImports]
        return wmi
    except ImportError:
        log.debug("WMI not available — temperatures may be unavailable")
        return None


def _read_cpu_temp_wmi() -> SensorReading | None:
    """Try to read CPU temperature via WMI."""
    wmi_mod = _try_import_wmi()
    if wmi_mod is None:
        return None
    try:
        w = wmi_mod.WMI(namespace="root\\OpenHardwareMonitor")
        sensors = w.Sensor()
        for sensor in sensors:
            if sensor.SensorType == "Temperature" and "CPU" in sensor.Name:
                return SensorReading(
                    SensorType.CPU_TEMP, sensor.Name,
                    float(sensor.Value), "°C", time.time(),
                )
    except Exception:
        log.debug("WMI temperature read failed", exc_info=True)
    return None


class WindowsSensorPort(SensorPort):
    """SensorPort for Windows using psutil + optional WMI."""

    def __init__(self) -> None:
        self._prev_net_io: object | None = None
        self._prev_net_time: float = 0.0

    def read_all(self) -> list[SensorReading]:
        log.debug("Reading all Windows sensors...")
        psutil = _try_import_psutil()
        if psutil is None:
            return []

        readings: list[SensorReading] = []
        now = time.time()

        # CPU load
        cpu_pct = psutil.cpu_percent(interval=0)
        readings.append(SensorReading(
            SensorType.CPU_LOAD, "CPU Load",
            round(cpu_pct, 1), "%", now,
        ))

        # CPU temperature (via psutil if available, fallback to WMI)
        try:
            temps = psutil.sensors_temperatures()
            if temps:
                for name, entries in temps.items():
                    for entry in entries:
                        readings.append(SensorReading(
                            SensorType.CPU_TEMP,
                            entry.label or f"{name}",
                            round(entry.current, 1), "°C", now,
                        ))
                        break  # first temp sensor
                    break
        except AttributeError:
            # sensors_temperatures() not available on all Windows builds
            cpu_temp = _read_cpu_temp_wmi()
            if cpu_temp:
                readings.append(cpu_temp)

        # RAM
        mem = psutil.virtual_memory()
        readings.extend([
            SensorReading(SensorType.RAM_SIZE, "RAM Total",
                          round(mem.total / (1024 ** 3), 1), "GB", now),
            SensorReading(SensorType.RAM_USED, "RAM Used",
                          round(mem.used / (1024 ** 3), 1), "GB", now),
            SensorReading(SensorType.RAM_AVAILABLE, "RAM Available",
                          round(mem.available / (1024 ** 3), 1), "GB", now),
            SensorReading(SensorType.RAM_USAGE_RATE, "RAM Usage",
                          round(mem.percent, 1), "%", now),
        ])

        # Network speeds
        readings.extend(self._read_network(psutil, now))

        log.debug("Windows sensors: %d readings", len(readings))
        return readings

    def read_type(self, sensor_type: int) -> SensorReading | None:
        for reading in self.read_all():
            if reading.sensor_type == sensor_type:
                return reading
        return None

    def _read_network(self, psutil: object, now: float) -> list[SensorReading]:
        """Calculate network speeds between successive reads."""
        try:
            net_io = psutil.net_io_counters()  # type: ignore[union-attr]
        except Exception:
            return []

        readings: list[SensorReading] = []
        dt = now - self._prev_net_time if self._prev_net_time > 0 else 0

        if dt > 0 and self._prev_net_io is not None:
            prev = self._prev_net_io
            dl = (net_io.bytes_recv - prev.bytes_recv) / dt / 1048576.0  # type: ignore[union-attr]
            ul = (net_io.bytes_sent - prev.bytes_sent) / dt / 1048576.0  # type: ignore[union-attr]
            readings = [
                SensorReading(SensorType.LAN_DOWNLOAD, "Download",
                              round(max(0, dl), 2), "MB/s", now),
                SensorReading(SensorType.LAN_UPLOAD, "Upload",
                              round(max(0, ul), 2), "MB/s", now),
            ]

        self._prev_net_io = net_io
        self._prev_net_time = now
        return readings
