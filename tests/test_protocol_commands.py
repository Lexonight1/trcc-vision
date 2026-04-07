"""Tests for device command builders and RGB565 conversion."""

from __future__ import annotations

import pytest

from trcc_vision.protocols.commands import (
    CMD_BACKGROUND,
    CMD_BRIGHTNESS,
    CMD_FILE_NOTICE,
    CMD_ROTATION,
    CMD_SCREEN,
    CMD_SENSOR_DATA,
    CMD_VIDEO_LOOP,
    brightness,
    file_notice,
    image_to_rgb565,
    rotation,
    screen_power,
    sensor_data,
    set_background,
    video_loop,
)
from trcc_vision.protocols.message import HEADER, Message


class TestBrightness:
    def test_clamps_to_range(self) -> None:
        msg = brightness(150)
        assert msg.payload == bytes([0x00, 100])

    def test_zero(self) -> None:
        msg = brightness(0)
        assert msg.payload == bytes([0x00, 0])

    def test_command_byte(self) -> None:
        msg = brightness(50)
        assert msg.cmd == CMD_BRIGHTNESS


class TestScreenPower:
    def test_on(self) -> None:
        msg = screen_power(True)
        assert msg.cmd == CMD_SCREEN
        assert msg.payload == bytes([1])

    def test_off(self) -> None:
        msg = screen_power(False)
        assert msg.payload == bytes([0])


class TestRotation:
    def test_zero(self) -> None:
        msg = rotation(0)
        assert msg.cmd == CMD_ROTATION
        assert msg.payload == bytes([0])

    def test_90(self) -> None:
        assert rotation(90).payload == bytes([1])

    def test_180(self) -> None:
        assert rotation(180).payload == bytes([2])

    def test_270(self) -> None:
        assert rotation(270).payload == bytes([3])

    def test_invalid_defaults_zero(self) -> None:
        assert rotation(45).payload == bytes([0])


class TestVideoLoop:
    def test_enable(self) -> None:
        msg = video_loop(True)
        assert msg.cmd == CMD_VIDEO_LOOP
        assert msg.payload == bytes([1])


class TestSensorData:
    def test_builds_payload(self) -> None:
        msg = sensor_data(cpu_core_temp=65, gpu_temp=72)
        assert msg.cmd == CMD_SENSOR_DATA
        # Payload has all sensor values packed
        assert len(msg.payload) > 0

    def test_all_zeros(self) -> None:
        msg = sensor_data()
        assert msg.cmd == CMD_SENSOR_DATA


class TestFileNotice:
    def test_pads_filename(self) -> None:
        msg = file_notice("00.png")
        assert msg.cmd == CMD_FILE_NOTICE
        assert len(msg.payload) == 32
        assert msg.payload[:6] == b"00.png"
        assert msg.payload[6:] == b"\x00" * 26

    def test_truncates_long_name(self) -> None:
        msg = file_notice("a" * 50)
        assert len(msg.payload) == 32


class TestSetBackground:
    def test_builds_payload(self) -> None:
        msg = set_background(bg_type=0, show_data=1, unit="°C", filename="00.png")
        assert msg.cmd == CMD_BACKGROUND
        # type(1) + show_data(2) + unit(3) + filename(32) = 38
        assert len(msg.payload) == 38


class TestSerialize:
    def test_message_roundtrip(self) -> None:
        msg = brightness(80)
        raw = msg.serialize()
        assert raw[:2] == HEADER
        parsed = Message.parse(raw)
        assert parsed is not None
        assert parsed.cmd == CMD_BRIGHTNESS


class TestRGB565:
    def test_pure_red(self) -> None:
        from PIL import Image

        img = Image.new("RGB", (1, 1), (255, 0, 0))
        data = image_to_rgb565(img)
        assert len(data) == 2
        # Red 0xF8 << 8 = 0xF800, LE = 0x00 0xF8
        assert data == bytes([0x00, 0xF8])

    def test_pure_green(self) -> None:
        from PIL import Image

        img = Image.new("RGB", (1, 1), (0, 255, 0))
        data = image_to_rgb565(img)
        # Green 0xFC << 3 = 0x07E0, LE = 0xE0 0x07
        assert data == bytes([0xE0, 0x07])

    def test_pure_blue(self) -> None:
        from PIL import Image

        img = Image.new("RGB", (1, 1), (0, 0, 255))
        data = image_to_rgb565(img)
        # Blue 255 >> 3 = 0x1F, LE = 0x1F 0x00
        assert data == bytes([0x1F, 0x00])

    def test_output_size(self) -> None:
        from PIL import Image

        img = Image.new("RGB", (10, 10), (128, 128, 128))
        data = image_to_rgb565(img)
        assert len(data) == 10 * 10 * 2

    def test_rejects_non_image(self) -> None:
        with pytest.raises(TypeError):
            image_to_rgb565("not an image")  # type: ignore[arg-type]


class TestRGB565Numpy:
    def test_matches_pure_python(self) -> None:
        from PIL import Image

        from trcc_vision.protocols.commands import image_to_rgb565_numpy

        img = Image.new("RGB", (4, 4), (200, 100, 50))
        pure = image_to_rgb565(img)
        fast = image_to_rgb565_numpy(img)
        assert pure == fast

    def test_480x480_size(self) -> None:
        from PIL import Image

        from trcc_vision.protocols.commands import image_to_rgb565_numpy

        img = Image.new("RGB", (480, 480), (0, 0, 0))
        data = image_to_rgb565_numpy(img)
        assert len(data) == 480 * 480 * 2
