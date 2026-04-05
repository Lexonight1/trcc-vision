"""Linux sensor backend — reads directly from sysfs/procfs. Zero dependencies.

Works on every Linux distro with kernel 2.6.26+ (hwmon subsystem).
No lm-sensors, psutil, or any other package required.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path

from trcc_vision.core.enums import SensorType
from trcc_vision.core.models import SensorReading
from trcc_vision.core.ports import SensorPort

log = logging.getLogger(__name__)

HWMON_ROOT = Path("/sys/class/hwmon")
PROC_STAT = Path("/proc/stat")
PROC_MEMINFO = Path("/proc/meminfo")
PROC_NET_DEV = Path("/proc/net/dev")


def _read_sysfs(path: Path) -> str | None:
    """Read a sysfs file, return None on failure."""
    try:
        return path.read_text().strip()
    except (OSError, PermissionError):
        return None


def _read_sysfs_int(path: Path) -> int | None:
    """Read a sysfs file as int, return None on failure."""
    val = _read_sysfs(path)
    if val is None:
        return None
    try:
        return int(val)
    except ValueError:
        return None


class HwmonDevice:
    """A single hwmon device (e.g. coretemp, amdgpu, nct6775)."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.name = _read_sysfs(path / "name") or "unknown"

    def read_temps(self) -> list[SensorReading]:
        """Read all temperature inputs (temp*_input, millidegrees C)."""
        readings: list[SensorReading] = []
        for inp in sorted(self.path.glob("temp*_input")):
            raw = _read_sysfs_int(inp)
            if raw is None:
                continue
            temp_c = raw / 1000.0
            idx = inp.name.replace("temp", "").replace("_input", "")
            label_path = inp.parent / f"temp{idx}_label"
            label = _read_sysfs(label_path) or f"{self.name} temp{idx}"
            readings.append(SensorReading(
                sensor_type=SensorType.CPU_TEMP,  # refined by caller
                label=label,
                value=temp_c,
                unit="°C",
                timestamp=time.time(),
            ))
        return readings

    def read_fans(self) -> list[SensorReading]:
        """Read all fan inputs (fan*_input, RPM)."""
        readings: list[SensorReading] = []
        for inp in sorted(self.path.glob("fan*_input")):
            raw = _read_sysfs_int(inp)
            if raw is None:
                continue
            idx = inp.name.replace("fan", "").replace("_input", "")
            label_path = inp.parent / f"fan{idx}_label"
            label = _read_sysfs(label_path) or f"{self.name} fan{idx}"
            readings.append(SensorReading(
                sensor_type=SensorType.CPU_FAN_SPEED,
                label=label,
                value=float(raw),
                unit="RPM",
                timestamp=time.time(),
            ))
        return readings


class ProcStatReader:
    """Reads CPU load from /proc/stat."""

    def __init__(self) -> None:
        self._prev_idle: int = 0
        self._prev_total: int = 0

    def read_cpu_load(self) -> SensorReading | None:
        """Calculate CPU load % between two reads."""
        raw = _read_sysfs(PROC_STAT)
        if raw is None:
            return None

        for line in raw.splitlines():
            if line.startswith("cpu "):
                fields = [int(x) for x in line.split()[1:]]
                idle = fields[3] + (fields[4] if len(fields) > 4 else 0)
                total = sum(fields)

                diff_idle = idle - self._prev_idle
                diff_total = total - self._prev_total
                self._prev_idle = idle
                self._prev_total = total

                if diff_total == 0:
                    return None

                load = 100.0 * (1.0 - diff_idle / diff_total)
                return SensorReading(
                    sensor_type=SensorType.CPU_LOAD,
                    label="CPU Load",
                    value=round(load, 1),
                    unit="%",
                    timestamp=time.time(),
                )
        return None


def read_meminfo() -> list[SensorReading]:
    """Read RAM stats from /proc/meminfo."""
    raw = _read_sysfs(PROC_MEMINFO)
    if raw is None:
        return []

    mem: dict[str, int] = {}
    for line in raw.splitlines():
        parts = line.split()
        if len(parts) >= 2:
            key = parts[0].rstrip(":")
            try:
                mem[key] = int(parts[1])  # kB
            except ValueError:
                continue

    readings: list[SensorReading] = []
    total_kb = mem.get("MemTotal", 0)
    avail_kb = mem.get("MemAvailable", mem.get("MemFree", 0))
    used_kb = total_kb - avail_kb

    if total_kb > 0:
        total_gb = total_kb / 1048576.0
        used_gb = used_kb / 1048576.0
        avail_gb = avail_kb / 1048576.0
        usage_pct = 100.0 * used_kb / total_kb

        readings.extend([
            SensorReading(SensorType.RAM_SIZE, "RAM Total",
                          round(total_gb, 1), "GB", time.time()),
            SensorReading(SensorType.RAM_USED, "RAM Used",
                          round(used_gb, 1), "GB", time.time()),
            SensorReading(SensorType.RAM_AVAILABLE, "RAM Available",
                          round(avail_gb, 1), "GB", time.time()),
            SensorReading(SensorType.RAM_USAGE_RATE, "RAM Usage",
                          round(usage_pct, 1), "%", time.time()),
        ])

    return readings


class NetDevReader:
    """Reads network speeds from /proc/net/dev."""

    def __init__(self) -> None:
        self._prev_rx: int = 0
        self._prev_tx: int = 0
        self._prev_time: float = 0.0

    def read_speeds(self) -> list[SensorReading]:
        """Calculate network upload/download speeds in MB/s."""
        raw = _read_sysfs(PROC_NET_DEV)
        if raw is None:
            return []

        total_rx = 0
        total_tx = 0
        for line in raw.splitlines()[2:]:  # skip headers
            parts = line.split()
            if len(parts) < 10:
                continue
            iface = parts[0].rstrip(":")
            if iface == "lo":
                continue
            total_rx += int(parts[1])
            total_tx += int(parts[9])

        now = time.time()
        dt = now - self._prev_time if self._prev_time > 0 else 0

        readings: list[SensorReading] = []
        if dt > 0:
            dl_mbps = (total_rx - self._prev_rx) / dt / 1048576.0
            ul_mbps = (total_tx - self._prev_tx) / dt / 1048576.0
            readings = [
                SensorReading(SensorType.LAN_DOWNLOAD, "Download",
                              round(max(0, dl_mbps), 2), "MB/s", now),
                SensorReading(SensorType.LAN_UPLOAD, "Upload",
                              round(max(0, ul_mbps), 2), "MB/s", now),
            ]

        self._prev_rx = total_rx
        self._prev_tx = total_tx
        self._prev_time = now
        return readings


class LinuxSensorPort(SensorPort):
    """SensorPort implementation using sysfs/procfs. Zero dependencies."""

    def __init__(self) -> None:
        self._cpu_reader = ProcStatReader()
        self._net_reader = NetDevReader()
        self._hwmon_devices: list[HwmonDevice] | None = None

    def _discover_hwmon(self) -> list[HwmonDevice]:
        """Discover all hwmon devices once."""
        if self._hwmon_devices is not None:
            return self._hwmon_devices

        self._hwmon_devices = []
        if HWMON_ROOT.exists():
            for entry in sorted(HWMON_ROOT.iterdir()):
                resolved = entry.resolve()
                if resolved.is_dir():
                    self._hwmon_devices.append(HwmonDevice(resolved))
                    log.debug("Found hwmon: %s (%s)", resolved, _read_sysfs(resolved / "name"))

        return self._hwmon_devices

    def read_all(self) -> list[SensorReading]:
        """Read all available sensors."""
        readings: list[SensorReading] = []

        # hwmon temps and fans
        for dev in self._discover_hwmon():
            readings.extend(dev.read_temps())
            readings.extend(dev.read_fans())

        # CPU load
        cpu_load = self._cpu_reader.read_cpu_load()
        if cpu_load:
            readings.append(cpu_load)

        # RAM
        readings.extend(read_meminfo())

        # Network
        readings.extend(self._net_reader.read_speeds())

        return readings

    def read_type(self, sensor_type: int) -> SensorReading | None:
        """Read a specific sensor type."""
        for reading in self.read_all():
            if reading.sensor_type == sensor_type:
                return reading
        return None
