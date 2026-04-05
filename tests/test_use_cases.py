"""Tests for use cases — emulate real app flow through AppContext pattern.

Each test: create services via fixtures → build use case → execute → assert
result + verify events published. This mirrors how CLI/GUI/API use the app.
"""

from __future__ import annotations

from trcc_vision.core.enums import SensorType
from trcc_vision.core.events import (
    DeviceConnected,
    DeviceDisconnected,
    Event,
    EventBus,
    SensorUpdated,
)
from trcc_vision.core.models import DeviceInfo, FanCurvePoint
from trcc_vision.core.use_cases.device_ops import (
    ConnectDevice,
    DetectDevices,
    DisconnectDevice,
    GetDeviceStatus,
)
from trcc_vision.core.use_cases.fan_ops import GetFanStates, SetFanCurve, SetFanDuty
from trcc_vision.core.use_cases.sensor_ops import ReadAllSensors, ReadSensor
from trcc_vision.core.use_cases.system_ops import GetSystemInfo, RunDoctor
from trcc_vision.services.device import DeviceService
from trcc_vision.services.fan import FanService
from trcc_vision.services.sensor import SensorService

from .conftest import StubFanPort

# ── Sensor Use Cases ────────────────────────────────────────────────────


class TestReadAllSensors:
    """Emulates: adapter calls read_all_sensors.execute(), gets readings + event."""

    def test_returns_all_readings(
        self, sensor_service: SensorService, event_bus: EventBus,
    ) -> None:
        uc = ReadAllSensors(sensor_service, event_bus)
        result = uc.execute()
        assert len(result) == 4

    def test_publishes_sensor_updated_event(
        self,
        sensor_service: SensorService,
        event_bus: EventBus,
        event_collector: list[Event],
    ) -> None:
        uc = ReadAllSensors(sensor_service, event_bus)
        uc.execute()
        sensor_events = [e for e in event_collector if isinstance(e, SensorUpdated)]
        assert len(sensor_events) == 1
        assert len(sensor_events[0].readings) == 4

    def test_caches_for_subsequent_single_reads(
        self, sensor_service: SensorService, event_bus: EventBus,
    ) -> None:
        ReadAllSensors(sensor_service, event_bus).execute()
        single = ReadSensor(sensor_service)
        cpu = single.execute(SensorType.CPU_TEMP)
        assert cpu is not None
        assert cpu.value == 55.0


class TestReadSensor:
    def test_returns_none_when_no_data(
        self, empty_sensor_port: object,
    ) -> None:
        svc = SensorService(empty_sensor_port)  # type: ignore[arg-type]
        uc = ReadSensor(svc)
        assert uc.execute(SensorType.HDD_TEMP) is None


# ── Device Use Cases ────────────────────────────────────────────────────


class TestDeviceLifecycle:
    """Emulates full device flow: detect → connect → status → disconnect."""

    def test_detect_returns_list(
        self, device_service: DeviceService,
    ) -> None:
        uc = DetectDevices(device_service)
        result = uc.execute()
        assert isinstance(result, list)

    def test_connect_then_status(
        self,
        device_service: DeviceService,
        event_bus: EventBus,
        event_collector: list[Event],
        sample_device: DeviceInfo,
    ) -> None:
        # Connect
        connect = ConnectDevice(device_service, event_bus)
        assert connect.execute(sample_device) is True

        # Verify event fired
        connected_events = [
            e for e in event_collector if isinstance(e, DeviceConnected)
        ]
        assert len(connected_events) == 1
        assert connected_events[0].device.name == "TR-VISION Test"

        # Check status
        status = GetDeviceStatus(device_service).execute()
        assert status.connected is True
        assert status.device is not None
        assert status.device.address == "127.0.0.1:5555"

    def test_disconnect_after_connect(
        self,
        device_service: DeviceService,
        event_bus: EventBus,
        event_collector: list[Event],
        sample_device: DeviceInfo,
    ) -> None:
        ConnectDevice(device_service, event_bus).execute(sample_device)
        disconnect = DisconnectDevice(device_service, event_bus)
        assert disconnect.execute() is True

        disconnected = [
            e for e in event_collector if isinstance(e, DeviceDisconnected)
        ]
        assert len(disconnected) == 1

        status = GetDeviceStatus(device_service).execute()
        assert status.connected is False

    def test_status_when_never_connected(
        self, device_service: DeviceService,
    ) -> None:
        status = GetDeviceStatus(device_service).execute()
        assert status.connected is False
        assert status.device is None


# ── Fan Use Cases ───────────────────────────────────────────────────────


class TestFanUseCases:
    """Emulates: adapter reads fans, sets duty, applies curve."""

    def test_get_states_empty(self, fan_service: FanService) -> None:
        uc = GetFanStates(fan_service)
        assert uc.execute() == []

    def test_set_duty_then_read(
        self, fan_service: FanService, fan_port: StubFanPort,
    ) -> None:
        SetFanDuty(fan_service).execute(0, 75)
        assert fan_port.duties[0] == 75

        states = GetFanStates(fan_service).execute()
        assert len(states) == 1
        assert states[0].duty_percent == 75

    def test_set_curve(self, fan_service: FanService) -> None:
        points = [FanCurvePoint(30, 20), FanCurvePoint(60, 80)]
        assert SetFanCurve(fan_service).execute(0, points) is True


# ── System Use Cases ────────────────────────────────────────────────────


class TestSystemUseCases:
    """Emulates: adapter calls system info and doctor checks."""

    def test_system_info(self) -> None:
        info = GetSystemInfo().execute()
        assert info.app_version is not None
        assert info.python_version is not None
        assert info.platform_name in ("linux", "macos", "windows", "bsd", "unknown")

    def test_doctor_python_check_passes(self) -> None:
        results = RunDoctor().execute()
        assert len(results) > 0
        python_check = next(r for r in results if "Python" in r.name)
        assert python_check.passed is True

    def test_doctor_pillow_check(self) -> None:
        results = RunDoctor().execute()
        pillow = next(r for r in results if "Pillow" in r.name)
        assert pillow.passed is True  # Pillow is a project dependency
