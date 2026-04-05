"""macOS sensor backend — reads via sysctl, ioreg, and system tools.

Zero Python dependencies beyond stdlib. Uses subprocess calls to system
binaries that exist on every macOS install (10.15+).

CPU temp requires either:
- `sudo powermetrics` (Apple Silicon / Intel with SMC)
- Third-party `osx-cpu-temp` if installed
Falls back gracefully if neither is available.
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


def _run(cmd: list[str]) -> str | None:
    """Run a system command, return stdout or None on failure."""
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=_CMD_TIMEOUT,
        )
        if result.returncode == 0:
            return result.stdout.strip()
        log.debug("Command failed (rc=%d): %s", result.returncode, " ".join(cmd))
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        log.debug("Command unavailable: %s — %s", " ".join(cmd), e)
    return None


def _read_sysctl(key: str) -> str | None:
    """Read a single sysctl value."""
    out = _run(["sysctl", "-n", key])
    return out


# ── CPU / RAM ───────────────────────────────────────────────────────────


class _CpuLoadReader:
    """Reads CPU load from vm_stat + sysctl."""

    def read_cpu_load(self) -> SensorReading | None:
        # sysctl gives instantaneous load averages
        raw = _read_sysctl("vm.loadavg")
        if raw is None:
            return None
        # Format: "{ 1.23 2.34 3.45 }" — take 1-minute average
        match = re.search(r"[\d.]+", raw)
        if not match:
            return None
        # Normalize to percentage (load / ncpu * 100)
        ncpu_raw = _read_sysctl("hw.ncpu")
        ncpu = int(ncpu_raw) if ncpu_raw else 1
        load = float(match.group()) / ncpu * 100.0
        return SensorReading(
            SensorType.CPU_LOAD, "CPU Load",
            round(min(load, 100.0), 1), "%", time.time(),
        )


def _read_ram() -> list[SensorReading]:
    """Read RAM stats via sysctl + vm_stat."""
    readings: list[SensorReading] = []
    total_raw = _read_sysctl("hw.memsize")
    if total_raw is None:
        return readings

    total_bytes = int(total_raw)
    total_gb = total_bytes / (1024 ** 3)

    # vm_stat gives page-level stats
    vm_out = _run(["vm_stat"])
    if vm_out is None:
        return [SensorReading(
            SensorType.RAM_SIZE, "RAM Total",
            round(total_gb, 1), "GB", time.time(),
        )]

    pages: dict[str, int] = {}
    for line in vm_out.splitlines():
        match = re.match(r'(.+?):\s+(\d+)', line)
        if match:
            pages[match.group(1).strip()] = int(match.group(2))

    page_size_raw = _read_sysctl("hw.pagesize")
    page_size = int(page_size_raw) if page_size_raw else 4096

    free_pages = pages.get("Pages free", 0) + pages.get("Pages speculative", 0)
    avail_bytes = free_pages * page_size
    used_bytes = total_bytes - avail_bytes
    usage_pct = 100.0 * used_bytes / total_bytes if total_bytes > 0 else 0

    now = time.time()
    readings.extend([
        SensorReading(SensorType.RAM_SIZE, "RAM Total",
                      round(total_gb, 1), "GB", now),
        SensorReading(SensorType.RAM_USED, "RAM Used",
                      round(used_bytes / (1024 ** 3), 1), "GB", now),
        SensorReading(SensorType.RAM_AVAILABLE, "RAM Available",
                      round(avail_bytes / (1024 ** 3), 1), "GB", now),
        SensorReading(SensorType.RAM_USAGE_RATE, "RAM Usage",
                      round(usage_pct, 1), "%", now),
    ])
    return readings


# ── CPU Temperature ─────────────────────────────────────────────────────


def _read_cpu_temp() -> SensorReading | None:
    """Try multiple methods to get CPU temperature on macOS."""
    # Method 1: osx-cpu-temp (third-party, if installed)
    out = _run(["osx-cpu-temp"])
    if out:
        match = re.search(r"([\d.]+)\s*°?C", out)
        if match:
            return SensorReading(
                SensorType.CPU_TEMP, "CPU Temperature",
                float(match.group(1)), "°C", time.time(),
            )

    # Method 2: powermetrics (requires sudo, may not work without privileges)
    out = _run(["sudo", "-n", "powermetrics", "--samplers", "smc", "-i1", "-n1"])
    if out:
        match = re.search(r"CPU die temperature:\s*([\d.]+)\s*C", out)
        if match:
            return SensorReading(
                SensorType.CPU_TEMP, "CPU Temperature",
                float(match.group(1)), "°C", time.time(),
            )

    log.debug("No CPU temperature source available on macOS")
    return None


# ── Network ─────────────────────────────────────────────────────────────


class _NetStatReader:
    """Reads network throughput from netstat."""

    def __init__(self) -> None:
        self._prev_rx: int = 0
        self._prev_tx: int = 0
        self._prev_time: float = 0.0

    def read_speeds(self) -> list[SensorReading]:
        out = _run(["netstat", "-ib"])
        if out is None:
            return []

        total_rx = 0
        total_tx = 0
        for line in out.splitlines()[1:]:
            parts = line.split()
            if len(parts) < 10:
                continue
            iface = parts[0]
            if iface.startswith("lo"):
                continue
            try:
                total_rx += int(parts[6])  # Ibytes
                total_tx += int(parts[9])  # Obytes
            except (ValueError, IndexError):
                continue

        now = time.time()
        dt = now - self._prev_time if self._prev_time > 0 else 0

        readings: list[SensorReading] = []
        if dt > 0:
            dl = (total_rx - self._prev_rx) / dt / 1048576.0
            ul = (total_tx - self._prev_tx) / dt / 1048576.0
            readings = [
                SensorReading(SensorType.LAN_DOWNLOAD, "Download",
                              round(max(0, dl), 2), "MB/s", now),
                SensorReading(SensorType.LAN_UPLOAD, "Upload",
                              round(max(0, ul), 2), "MB/s", now),
            ]

        self._prev_rx = total_rx
        self._prev_tx = total_tx
        self._prev_time = now
        return readings


# ── Port ────────────────────────────────────────────────────────────────


class MacOSSensorPort(SensorPort):
    """SensorPort for macOS using sysctl, vm_stat, netstat."""

    def __init__(self) -> None:
        self._cpu_load = _CpuLoadReader()
        self._net = _NetStatReader()

    def read_all(self) -> list[SensorReading]:
        log.debug("Reading all macOS sensors...")
        readings: list[SensorReading] = []

        cpu_temp = _read_cpu_temp()
        if cpu_temp:
            readings.append(cpu_temp)

        cpu_load = self._cpu_load.read_cpu_load()
        if cpu_load:
            readings.append(cpu_load)

        readings.extend(_read_ram())
        readings.extend(self._net.read_speeds())

        log.debug("macOS sensors: %d readings", len(readings))
        return readings

    def read_type(self, sensor_type: int) -> SensorReading | None:
        for reading in self.read_all():
            if reading.sensor_type == sensor_type:
                return reading
        return None
