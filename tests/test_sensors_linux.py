"""Tests for Linux sysfs/procfs sensor backend."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

from trcc_vision.core.enums import SensorType
from trcc_vision.infrastructure.sensors_linux import (
    HwmonDevice,
    LinuxSensorPort,
    NetDevReader,
    ProcStatReader,
    read_meminfo,
)

if TYPE_CHECKING:
    from pathlib import Path

MOD = "trcc_vision.infrastructure.sensors_linux"


# ── Hwmon Device ────────────────────────────────────────────────────────


class TestHwmonDevice:
    """Reads temperature and fan data from fake hwmon sysfs files."""

    def test_read_temps(self, fake_hwmon: Path) -> None:
        dev = HwmonDevice(fake_hwmon)
        assert dev.name == "coretemp"
        temps = dev.read_temps()
        assert len(temps) == 2
        assert temps[0].label == "Core 0"
        assert temps[0].value == 55.0
        assert temps[0].unit == "°C"
        assert temps[1].value == 60.0

    def test_read_fans(self, fake_hwmon: Path) -> None:
        dev = HwmonDevice(fake_hwmon)
        fans = dev.read_fans()
        assert len(fans) == 2
        assert fans[0].value == 1200.0
        assert fans[0].unit == "RPM"
        assert fans[1].value == 900.0

    def test_empty_hwmon_returns_nothing(self, tmp_path: Path) -> None:
        hwmon = tmp_path / "hwmon_empty"
        hwmon.mkdir()
        (hwmon / "name").write_text("empty\n")
        dev = HwmonDevice(hwmon)
        assert dev.read_temps() == []
        assert dev.read_fans() == []


# ── CPU Load ────────────────────────────────────────────────────────────


class TestProcStatReader:
    """Calculates CPU load % from successive /proc/stat reads."""

    def test_cpu_load_between_two_reads(self) -> None:
        reader = ProcStatReader()
        stat1 = "cpu  100 0 50 800 50 0 0 0 0 0\nother"
        stat2 = "cpu  200 0 100 850 50 0 0 0 0 0\nother"

        with patch(f"{MOD}._read_sysfs", return_value=stat1):
            reader.read_cpu_load()  # baseline

        with patch(f"{MOD}._read_sysfs", return_value=stat2):
            result = reader.read_cpu_load()
            assert result is not None
            assert result.sensor_type == SensorType.CPU_LOAD
            assert result.value == 75.0
            assert result.unit == "%"

    def test_returns_none_when_proc_missing(self) -> None:
        reader = ProcStatReader()
        with patch(f"{MOD}._read_sysfs", return_value=None):
            assert reader.read_cpu_load() is None


# ── Memory ──────────────────────────────────────────────────────────────


class TestMeminfo:
    """Parses /proc/meminfo into RAM sensor readings."""

    def test_parses_all_fields(self) -> None:
        fake = (
            "MemTotal:       16384000 kB\n"
            "MemFree:         2048000 kB\n"
            "MemAvailable:    8192000 kB\n"
            "Buffers:          512000 kB\n"
        )
        with patch(f"{MOD}._read_sysfs", return_value=fake):
            readings = read_meminfo()

        by_type = {r.sensor_type: r for r in readings}
        assert SensorType.RAM_SIZE in by_type
        assert SensorType.RAM_USED in by_type
        assert SensorType.RAM_AVAILABLE in by_type
        assert SensorType.RAM_USAGE_RATE in by_type
        assert by_type[SensorType.RAM_SIZE].value == 15.6
        assert by_type[SensorType.RAM_USAGE_RATE].unit == "%"

    def test_missing_file_returns_empty(self) -> None:
        with patch(f"{MOD}._read_sysfs", return_value=None):
            assert read_meminfo() == []


# ── Network ─────────────────────────────────────────────────────────────


class TestNetDevReader:
    """Calculates upload/download speed from successive /proc/net/dev reads."""

    def test_speed_after_two_reads(self) -> None:
        reader = NetDevReader()
        net1 = (
            "Inter-| Receive\n"
            " face |bytes ...\n"
            "    lo: 1000 0 0 0 0 0 0 0 1000 0 0 0 0 0 0 0\n"
            "  eth0: 1000000 0 0 0 0 0 0 0 500000 0 0 0 0 0 0 0\n"
        )
        net2 = (
            "Inter-| Receive\n"
            " face |bytes ...\n"
            "    lo: 2000 0 0 0 0 0 0 0 2000 0 0 0 0 0 0 0\n"
            "  eth0: 2048576 0 0 0 0 0 0 0 1548576 0 0 0 0 0 0 0\n"
        )

        with patch(f"{MOD}._read_sysfs", return_value=net1):
            assert reader.read_speeds() == []  # baseline

        reader._prev_time -= 1.0  # simulate 1 second elapsed

        with patch(f"{MOD}._read_sysfs", return_value=net2):
            speeds = reader.read_speeds()
            assert len(speeds) == 2
            dl = next(r for r in speeds if r.sensor_type == SensorType.LAN_DOWNLOAD)
            ul = next(r for r in speeds if r.sensor_type == SensorType.LAN_UPLOAD)
            assert dl.value == 1.0
            assert ul.value == 1.0
            assert dl.unit == "MB/s"


# ── LinuxSensorPort (integration) ──────────────────────────────────────


class TestLinuxSensorPort:
    """Full port reads hwmon + proc combined."""

    def test_reads_temps_and_fans(self, fake_hwmon: Path, tmp_path: Path) -> None:
        port = LinuxSensorPort()
        port._hwmon_devices = [HwmonDevice(fake_hwmon)]

        mock_stat = patch(f"{MOD}.PROC_STAT", tmp_path / "nonexistent")
        mock_mem = patch(f"{MOD}.PROC_MEMINFO", tmp_path / "nonexistent")
        with mock_stat, mock_mem:
            readings = port.read_all()

        temps = [r for r in readings if r.unit == "°C"]
        fans = [r for r in readings if r.unit == "RPM"]
        assert len(temps) == 2
        assert len(fans) == 2
        assert temps[0].value == 55.0
        assert fans[0].value == 1200.0
