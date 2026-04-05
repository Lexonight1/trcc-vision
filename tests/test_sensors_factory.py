"""Tests for cross-platform sensor factory and platform-specific backends."""

from __future__ import annotations

from unittest.mock import patch

from trcc_vision.core.enums import SensorType
from trcc_vision.infrastructure.platform import Platform
from trcc_vision.infrastructure.sensors import NullSensorPort, create_sensor_port

MOD = "trcc_vision.infrastructure.sensors"


class TestSensorFactory:
    """Factory returns the correct backend per platform."""

    def test_linux_returns_linux_port(self) -> None:
        with patch(f"{MOD}.current_platform", return_value=Platform.LINUX):
            port = create_sensor_port()
        from trcc_vision.infrastructure.sensors_linux import LinuxSensorPort
        assert isinstance(port, LinuxSensorPort)

    def test_unknown_returns_null_port(self) -> None:
        with patch(f"{MOD}.current_platform", return_value=Platform.UNKNOWN):
            port = create_sensor_port()
        assert isinstance(port, NullSensorPort)

    def test_null_port_returns_empty(self) -> None:
        port = NullSensorPort()
        assert port.read_all() == []
        assert port.read_type(SensorType.CPU_TEMP) is None


class TestMacOSSensorPort:
    """macOS sensor backend with mocked subprocess calls."""

    def test_cpu_load_from_sysctl(self) -> None:
        from trcc_vision.infrastructure.sensors_macos import _CpuLoadReader

        reader = _CpuLoadReader()
        mock_mod = "trcc_vision.infrastructure.sensors_macos._read_sysctl"
        with patch(mock_mod, side_effect=lambda k: {
            "vm.loadavg": "{ 0.50 0.60 0.70 }",
            "hw.ncpu": "4",
        }.get(k)):
            result = reader.read_cpu_load()
        assert result is not None
        assert result.sensor_type == SensorType.CPU_LOAD
        # 0.50 / 4 * 100 = 12.5%
        assert result.value == 12.5

    def test_ram_from_sysctl(self) -> None:
        from trcc_vision.infrastructure.sensors_macos import _read_ram

        def mock_sysctl(key: str) -> str | None:
            return {
                "hw.memsize": "17179869184",  # 16 GB
                "hw.pagesize": "4096",
            }.get(key)

        def mock_run(cmd: list[str]) -> str | None:
            if cmd[0] == "vm_stat":
                return (
                    "Mach Virtual Memory Statistics:\n"
                    "Pages free:          1048576.\n"
                    "Pages speculative:   0.\n"
                )
            return None

        sysctl_mod = "trcc_vision.infrastructure.sensors_macos._read_sysctl"
        run_mod = "trcc_vision.infrastructure.sensors_macos._run"
        with patch(sysctl_mod, side_effect=mock_sysctl), \
             patch(run_mod, side_effect=mock_run):
            readings = _read_ram()

        by_type = {r.sensor_type: r for r in readings}
        assert SensorType.RAM_SIZE in by_type
        assert by_type[SensorType.RAM_SIZE].value == 16.0

    def test_port_read_all(self) -> None:
        from trcc_vision.infrastructure.sensors_macos import MacOSSensorPort

        port = MacOSSensorPort()
        # With all subprocess calls failing, should return empty gracefully
        with patch("trcc_vision.infrastructure.sensors_macos._run", return_value=None), \
             patch("trcc_vision.infrastructure.sensors_macos._read_sysctl", return_value=None):
            readings = port.read_all()
        assert isinstance(readings, list)


class TestWindowsSensorPort:
    """Windows sensor backend with mocked psutil."""

    def test_returns_empty_without_psutil(self) -> None:
        from trcc_vision.infrastructure.sensors_windows import WindowsSensorPort

        port = WindowsSensorPort()
        with patch(
            "trcc_vision.infrastructure.sensors_windows._try_import_psutil",
            return_value=None,
        ):
            readings = port.read_all()
        assert readings == []


class TestBSDSensorPort:
    """BSD sensor backend with mocked sysctl."""

    def test_cpu_temp_freebsd(self) -> None:
        from trcc_vision.infrastructure.sensors_bsd import _read_cpu_temp

        with patch(
            "trcc_vision.infrastructure.sensors_bsd._sysctl",
            side_effect=lambda k: "55.0C" if k == "dev.cpu.0.temperature" else None,
        ):
            result = _read_cpu_temp()
        assert result is not None
        assert result.value == 55.0

    def test_cpu_temp_openbsd(self) -> None:
        from trcc_vision.infrastructure.sensors_bsd import _read_cpu_temp

        def mock_sysctl(key: str) -> str | None:
            if key == "hw.sensors.cpu0.temp0":
                return "62.00 degC"
            return None

        with patch("trcc_vision.infrastructure.sensors_bsd._sysctl", side_effect=mock_sysctl):
            result = _read_cpu_temp()
        assert result is not None
        assert result.value == 62.0

    def test_ram_freebsd(self) -> None:
        from trcc_vision.infrastructure.sensors_bsd import _read_ram

        def mock_sysctl(key: str) -> str | None:
            return {
                "hw.physmem": "8589934592",  # 8 GB
                "vm.stats.vm.v_free_count": "524288",
                "hw.pagesize": "4096",
            }.get(key)

        with patch("trcc_vision.infrastructure.sensors_bsd._sysctl", side_effect=mock_sysctl):
            readings = _read_ram()

        by_type = {r.sensor_type: r for r in readings}
        assert SensorType.RAM_SIZE in by_type
        assert by_type[SensorType.RAM_SIZE].value == 8.0
        assert SensorType.RAM_USED in by_type

    def test_port_graceful_on_missing_sysctl(self) -> None:
        from trcc_vision.infrastructure.sensors_bsd import BSDSensorPort

        port = BSDSensorPort()
        with patch("trcc_vision.infrastructure.sensors_bsd._sysctl", return_value=None):
            readings = port.read_all()
        assert readings == []
