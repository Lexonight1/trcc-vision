"""Tests for core domain models and boundary validation."""

from __future__ import annotations

from pathlib import Path

import pytest

from trcc_vision.core.enums import (
    ConnectionType,
    DisplayMode,
    ElementType,
    SensorType,
)
from trcc_vision.core.models import (
    DeviceInfo,
    DisplayState,
    FanCurvePoint,
    FanState,
    PlayFile,
    ThemeConfig,
    ThemeElement,
    ThemeInfo,
)

# ── DeviceInfo ──────────────────────────────────────────────────────────


class TestDeviceInfo:
    def test_defaults(self) -> None:
        dev = DeviceInfo(name="Test", connection=ConnectionType.ADB, address="12345")
        assert dev.lcd_width == 480
        assert dev.lcd_height == 480

    def test_frozen(self) -> None:
        dev = DeviceInfo(name="Test", connection=ConnectionType.ADB, address="12345")
        with pytest.raises(AttributeError):
            dev.name = "changed"  # type: ignore[misc]

    def test_empty_name_rejected(self) -> None:
        with pytest.raises(ValueError, match="name cannot be empty"):
            DeviceInfo(name="", connection=ConnectionType.ADB, address="127.0.0.1")

    def test_empty_address_rejected(self) -> None:
        with pytest.raises(ValueError, match="address cannot be empty"):
            DeviceInfo(name="Dev", connection=ConnectionType.ADB, address="")

    def test_zero_lcd_rejected(self) -> None:
        with pytest.raises(ValueError, match="positive"):
            DeviceInfo(name="Dev", connection=ConnectionType.ADB, address="x", lcd_width=0)


# ── FanState ────────────────────────────────────────────────────────────


class TestFanState:
    def test_duty_clamped(self) -> None:
        fs = FanState(channel=0, duty_percent=150)
        assert fs.duty_percent == 100

    def test_duty_clamped_negative(self) -> None:
        fs = FanState(channel=0, duty_percent=-10)
        assert fs.duty_percent == 0

    def test_negative_channel_rejected(self) -> None:
        with pytest.raises(ValueError, match="channel"):
            FanState(channel=-1)

    def test_negative_rpm_rejected(self) -> None:
        with pytest.raises(ValueError, match="RPM"):
            FanState(channel=0, rpm=-100)


# ── FanCurvePoint ───────────────────────────────────────────────────────


class TestFanCurvePoint:
    def test_valid(self) -> None:
        p = FanCurvePoint(temp_c=40, duty_percent=30)
        assert p.temp_c == 40
        assert p.duty_percent == 30

    def test_duty_clamped(self) -> None:
        p = FanCurvePoint(temp_c=50, duty_percent=200)
        assert p.duty_percent == 100


# ── ThemeElement ────────────────────────────────────────────────────────


class TestThemeElement:
    def test_data_element(self) -> None:
        elem = ThemeElement(
            element_type=ElementType.DATA,
            content="55℃",
            data_unit="℃",
            color="#000000",
        )
        assert elem.element_type == ElementType.DATA
        assert elem.font_family == "NI7SEG"

    def test_timer_element(self) -> None:
        elem = ThemeElement(element_type=ElementType.TIMER)
        assert elem.timer_type.value == 0

    def test_image_element(self) -> None:
        elem = ThemeElement(
            element_type=ElementType.IMAGE,
            image_file_path="bg.png",
            width=480,
            height=480,
            z_index=0,
        )
        assert elem.width == 480

    def test_negative_font_size_rejected(self) -> None:
        with pytest.raises(ValueError, match="font_size"):
            ThemeElement(element_type=ElementType.DATA, font_size=-1.0)

    def test_invalid_color_rejected(self) -> None:
        with pytest.raises(ValueError, match="hex"):
            ThemeElement(element_type=ElementType.DATA, color="red")

    def test_opacity_clamped(self) -> None:
        elem = ThemeElement(element_type=ElementType.DATA, opacity=1.5)
        assert elem.opacity == 1.0

    def test_negative_z_index_allowed(self) -> None:
        elem = ThemeElement(element_type=ElementType.VIDEO, z_index=-1)
        assert elem.z_index == -1


# ── ThemeConfig ─────────────────────────────────────────────────────────


class TestThemeConfig:
    def test_defaults(self) -> None:
        cfg = ThemeConfig()
        assert cfg.display_data is True
        assert cfg.display_image is True
        assert cfg.rotation == 0
        assert cfg.elements == []

    def test_with_elements(self) -> None:
        elem = ThemeElement(element_type=ElementType.TIMER, content="12:00")
        cfg = ThemeConfig(elements=[elem])
        assert len(cfg.elements) == 1
        assert cfg.elements[0].content == "12:00"


# ── DisplayState ────────────────────────────────────────────────────────


class TestDisplayState:
    def test_defaults(self) -> None:
        state = DisplayState()
        assert state.mode == DisplayMode.BACKGROUND
        assert state.brightness == 100
        assert state.theme is None

    def test_brightness_clamped(self) -> None:
        state = DisplayState(brightness=150)
        assert state.brightness == 100

    def test_negative_frame_rejected(self) -> None:
        with pytest.raises(ValueError, match="current_frame"):
            DisplayState(current_frame=-1)


# ── ThemeInfo ───────────────────────────────────────────────────────────


class TestThemeInfo:
    def test_basic(self) -> None:
        info = ThemeInfo(name="test_theme", path=Path("/tmp/theme"))
        assert info.has_background is True
        assert info.has_video is False

    def test_empty_name_rejected(self) -> None:
        with pytest.raises(ValueError, match="name cannot be empty"):
            ThemeInfo(name="", path=Path("/tmp/theme"))


# ── PlayFile ────────────────────────────────────────────────────────────


class TestPlayFile:
    def test_valid(self) -> None:
        pf = PlayFile(path=Path("/tmp/video.mp4"), name="video")
        assert pf.duration_ms == 0

    def test_empty_name_rejected(self) -> None:
        with pytest.raises(ValueError, match="name cannot be empty"):
            PlayFile(path=Path("/tmp/x.mp4"), name="")

    def test_negative_duration_rejected(self) -> None:
        with pytest.raises(ValueError, match="duration_ms"):
            PlayFile(path=Path("/tmp/x.mp4"), name="x", duration_ms=-1)


# ── SensorType enum ────────────────────────────────────────────────────


class TestSensorType:
    def test_cpu_temp_value(self) -> None:
        assert SensorType.CPU_TEMP == 0

    def test_gpu_temp_value(self) -> None:
        assert SensorType.GPU_TEMP == 13
