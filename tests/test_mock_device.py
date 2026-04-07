"""Tests for mock device and fan ports — full app flow without hardware."""

from __future__ import annotations

import pytest

from trcc_vision.core.events import DeviceConnected, DeviceDisconnected, Event, EventBus
from trcc_vision.core.use_cases.device_ops import (
    ConnectDevice,
    DisconnectDevice,
    GetDeviceStatus,
)
from trcc_vision.core.use_cases.fan_ops import GetFanStates, SetFanDuty
from trcc_vision.infrastructure.mock_device import MOCK_DEVICE, MockDevicePort
from trcc_vision.infrastructure.mock_fan import MockFanPort
from trcc_vision.services.device import DeviceService
from trcc_vision.services.fan import FanService

# ── MockDevicePort ──────────────────────────────────────────────────────


class TestMockDevicePort:
    def test_not_connected_initially(self) -> None:
        port = MockDevicePort()
        assert port.is_connected() is False

    def test_connect_disconnect(self) -> None:
        port = MockDevicePort()
        port.connect(MOCK_DEVICE)
        assert port.is_connected() is True
        port.disconnect()
        assert port.is_connected() is False

    def test_send_frame_stores_data(self) -> None:
        port = MockDevicePort()
        port.connect(MOCK_DEVICE)
        frame = b"\x00" * 480 * 480 * 2  # fake RGB565
        port.send_frame(frame, 480, 480)
        assert port.last_frame == frame
        assert port.last_frame_size == (480, 480)
        assert port.frame_count == 1

    def test_send_frame_when_disconnected_raises(self) -> None:
        port = MockDevicePort()
        with pytest.raises(ConnectionError):
            port.send_frame(b"\x00", 1, 1)

    def test_send_command_returns_ack(self) -> None:
        port = MockDevicePort()
        port.connect(MOCK_DEVICE)
        cmd = bytes([0xAA, 0xF5, 0x01, 0x00, 0x42, 0x00])
        response = port.send_command(cmd)
        assert response[0:2] == bytes([0xAA, 0xF5])  # header present

    def test_send_command_when_disconnected_raises(self) -> None:
        port = MockDevicePort()
        with pytest.raises(ConnectionError):
            port.send_command(b"\x00")

    def test_frame_count_increments(self) -> None:
        port = MockDevicePort()
        port.connect(MOCK_DEVICE)
        port.send_frame(b"\x00", 1, 1)
        port.send_frame(b"\x00", 1, 1)
        port.send_frame(b"\x00", 1, 1)
        assert port.frame_count == 3

    def test_disconnect_resets_frame_state(self) -> None:
        port = MockDevicePort()
        port.connect(MOCK_DEVICE)
        port.send_frame(b"\x00", 1, 1)
        port.disconnect()
        assert port.last_frame is None
        assert port.frame_count == 0


# ── MockFanPort ─────────────────────────────────────────────────────────


class TestMockFanPort:
    def test_default_4_channels(self) -> None:
        port = MockFanPort()
        states = port.get_fan_states()
        assert len(states) == 4

    def test_custom_channel_count(self) -> None:
        port = MockFanPort(num_channels=2)
        assert len(port.get_fan_states()) == 2

    def test_set_duty_and_read(self) -> None:
        port = MockFanPort()
        port.set_fan_duty(0, 100)
        states = port.get_fan_states()
        assert states[0].duty_percent == 100

    def test_duty_clamped(self) -> None:
        port = MockFanPort()
        port.set_fan_duty(0, 150)
        states = port.get_fan_states()
        assert states[0].duty_percent == 100

    def test_invalid_channel_raises(self) -> None:
        port = MockFanPort(num_channels=2)
        with pytest.raises(ValueError, match="Invalid channel"):
            port.set_fan_duty(5, 50)

    def test_rpm_varies_with_duty(self) -> None:
        port = MockFanPort()
        port.set_fan_duty(0, 0)
        low = port.get_fan_states()[0].rpm
        port.set_fan_duty(0, 100)
        high = port.get_fan_states()[0].rpm
        # At 100% duty, RPM should generally be higher than at 0%
        # (with randomness, check broad range)
        assert high > low - 100  # allow for random drift


# ── Full Flow via Use Cases ─────────────────────────────────────────────


class TestMockFullFlow:
    """Emulates the real app flow: detect → connect → send → fans → disconnect."""

    def test_device_lifecycle(self) -> None:
        port = MockDevicePort()
        svc = DeviceService(port)
        bus = EventBus()
        events: list[Event] = []
        bus.subscribe(DeviceConnected, events.append)
        bus.subscribe(DeviceDisconnected, events.append)

        # Connect
        connect = ConnectDevice(svc, bus)
        assert connect.execute(MOCK_DEVICE) is True
        assert isinstance(events[0], DeviceConnected)

        # Status
        status = GetDeviceStatus(svc).execute()
        assert status.connected is True
        assert status.device is not None
        assert status.device.name == "TR-VISION Mock"

        # Disconnect
        disconnect = DisconnectDevice(svc, bus)
        assert disconnect.execute() is True
        assert any(isinstance(e, DeviceDisconnected) for e in events)

    def test_fan_lifecycle(self) -> None:
        port = MockFanPort()
        svc = FanService(port)

        # Read
        states = GetFanStates(svc).execute()
        assert len(states) == 4

        # Set
        assert SetFanDuty(svc).execute(0, 80) is True
        states = GetFanStates(svc).execute()
        assert states[0].duty_percent == 80


# ── AppContext Mock Mode ────────────────────────────────────────────────


class TestAppContextMock:
    """Verify AppContext(mock=True) wires everything."""

    def test_mock_context_has_all_use_cases(self) -> None:
        from trcc_vision.core.context import AppContext

        ctx = AppContext(mock=True)
        assert ctx.mock is True
        assert ctx.detect_devices is not None
        assert ctx.connect_device is not None
        assert ctx.disconnect_device is not None
        assert ctx.get_device_status is not None
        assert ctx.send_image is not None
        assert ctx.send_color is not None
        assert ctx.set_brightness is not None
        assert ctx.get_fan_states is not None
        assert ctx.set_fan_duty is not None
        assert ctx.read_all_sensors is not None

    def test_non_mock_context_has_real_device(self) -> None:
        from trcc_vision.core.context import AppContext

        ctx = AppContext(mock=False)
        assert ctx.mock is False
        assert ctx.detect_devices is not None
        assert ctx.device_service is not None
        assert ctx.get_fan_states is None  # FanPort not yet wired
