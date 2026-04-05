"""Shared test fixtures — stubs, services, event bus, use cases.

All stubs properly implement their ABCs. Fixtures mirror real app wiring
through AppContext so tests emulate actual application flow.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from trcc_vision.core.enums import ConnectionType, SensorType
from trcc_vision.core.events import Event, EventBus
from trcc_vision.core.models import DeviceInfo, FanState, SensorReading
from trcc_vision.core.ports import DevicePort, FanPort, SensorPort
from trcc_vision.services.device import DeviceService
from trcc_vision.services.fan import FanService
from trcc_vision.services.sensor import SensorService

if TYPE_CHECKING:
    from pathlib import Path


# ── Stub Ports (proper ABC implementations) ────────────────────────────


class StubSensorPort(SensorPort):
    """Configurable sensor port that returns preset readings."""

    def __init__(self, readings: list[SensorReading] | None = None) -> None:
        self._readings = readings or []

    def read_all(self) -> list[SensorReading]:
        return list(self._readings)

    def read_type(self, sensor_type: int) -> SensorReading | None:
        return next(
            (r for r in self._readings if r.sensor_type == sensor_type),
            None,
        )


class StubFanPort(FanPort):
    """Fan port that records duty writes for assertion."""

    def __init__(self) -> None:
        self.duties: dict[int, int] = {}

    def get_fan_states(self) -> list[FanState]:
        return [
            FanState(channel=ch, duty_percent=d)
            for ch, d in sorted(self.duties.items())
        ]

    def set_fan_duty(self, channel: int, duty_percent: int) -> None:
        self.duties[channel] = duty_percent


class StubDevicePort(DevicePort):
    """Device port that tracks connection state and records sent frames."""

    def __init__(self) -> None:
        self._connected = False
        self.sent_frames: list[tuple[bytes, int, int]] = []
        self.sent_commands: list[bytes] = []

    def connect(self, device: DeviceInfo) -> None:
        self._connected = True

    def disconnect(self) -> None:
        self._connected = False

    def is_connected(self) -> bool:
        return self._connected

    def send_frame(self, data: bytes, width: int, height: int) -> None:
        self.sent_frames.append((data, width, height))

    def send_command(self, cmd: bytes) -> bytes:
        self.sent_commands.append(cmd)
        return b"\x00"


# ── Sample Data ─────────────────────────────────────────────────────────


SAMPLE_DEVICE = DeviceInfo(
    name="TR-VISION Test",
    connection=ConnectionType.ADB,
    address="127.0.0.1:5555",
    lcd_width=480,
    lcd_height=480,
)

SAMPLE_READINGS = [
    SensorReading(SensorType.CPU_TEMP, "CPU Package", 55.0, "°C"),
    SensorReading(SensorType.GPU_TEMP, "GPU Core", 65.0, "°C"),
    SensorReading(SensorType.CPU_LOAD, "CPU Load", 23.5, "%"),
    SensorReading(SensorType.RAM_USAGE_RATE, "RAM Usage", 48.2, "%"),
]


# ── Port Fixtures ───────────────────────────────────────────────────────


@pytest.fixture()
def sensor_port() -> StubSensorPort:
    """Sensor port preloaded with sample readings."""
    return StubSensorPort(SAMPLE_READINGS)


@pytest.fixture()
def empty_sensor_port() -> StubSensorPort:
    """Sensor port with no readings (simulates no hardware)."""
    return StubSensorPort()


@pytest.fixture()
def fan_port() -> StubFanPort:
    """Empty fan port for recording duty writes."""
    return StubFanPort()


@pytest.fixture()
def device_port() -> StubDevicePort:
    """Device port that tracks connections and frame sends."""
    return StubDevicePort()


# ── Service Fixtures ────────────────────────────────────────────────────


@pytest.fixture()
def sensor_service(sensor_port: StubSensorPort) -> SensorService:
    """SensorService wired to stub port with sample data."""
    return SensorService(sensor_port)


@pytest.fixture()
def fan_service(fan_port: StubFanPort) -> FanService:
    """FanService wired to stub port."""
    return FanService(fan_port)


@pytest.fixture()
def device_service(device_port: StubDevicePort) -> DeviceService:
    """DeviceService wired to stub port."""
    return DeviceService(device_port)


# ── Event Bus Fixtures ──────────────────────────────────────────────────


@pytest.fixture()
def event_bus() -> EventBus:
    """Fresh event bus for each test."""
    return EventBus()


@pytest.fixture()
def event_collector(event_bus: EventBus) -> list[Event]:
    """List that auto-collects all published events.

    Usage:
        def test_something(event_bus, event_collector):
            event_bus.publish(SomeEvent(...))
            assert len(event_collector) == 1
    """
    collected: list[Event] = []

    # Subscribe to all known event types
    from trcc_vision.core.events import (
        BrightnessChanged,
        DeviceConnected,
        DeviceDisconnected,
        PlaybackStateChanged,
        SensorUpdated,
        ThemeApplied,
    )

    for event_type in (
        SensorUpdated,
        DeviceConnected,
        DeviceDisconnected,
        PlaybackStateChanged,
        BrightnessChanged,
        ThemeApplied,
    ):
        event_bus.subscribe(event_type, collected.append)

    return collected


# ── Sample Data Fixture ─────────────────────────────────────────────────


@pytest.fixture()
def sample_device() -> DeviceInfo:
    """A valid DeviceInfo for testing."""
    return SAMPLE_DEVICE


# ── Hwmon Fixture (for Linux sensor tests) ──────────────────────────────


@pytest.fixture()
def fake_hwmon(tmp_path: Path) -> Path:
    """Create a fake hwmon directory with temp and fan files."""
    hwmon = tmp_path / "hwmon0"
    hwmon.mkdir()
    (hwmon / "name").write_text("coretemp\n")
    (hwmon / "temp1_input").write_text("55000\n")
    (hwmon / "temp1_label").write_text("Core 0\n")
    (hwmon / "temp2_input").write_text("60000\n")
    (hwmon / "temp2_label").write_text("Core 1\n")
    (hwmon / "fan1_input").write_text("1200\n")
    (hwmon / "fan2_input").write_text("900\n")
    return hwmon
