"""Device command builders — construct protocol messages for TR-VISION hardware.

Each function returns a Message ready to serialize and send via TCP.
Command bytes and payload layouts decoded from decompiled ADBFileHelper.cs.

Usage:
    from trcc_vision.protocols.commands import brightness, screen_on
    msg = brightness(80)
    device_protocol.send_message(msg)
"""

from __future__ import annotations

import struct

from trcc_vision.protocols.message import Message, pack_uint16_le

# ── Command bytes (decoded from obfuscated C#) ────────────────────────

CMD_BRIGHTNESS = 0x07       # Set LCD brightness (0-100)
CMD_SENSOR_DATA = 0x15      # Push sensor readings to device (21 = SET_BIOS)
CMD_FILE_NOTICE = 0x1F      # Image/video file operation (31)
CMD_BACKGROUND = 0x22       # Set background image (34)
CMD_SCREEN = 0x24           # Screen on/off (36)
CMD_VIDEO_LOOP = 0x26       # Video loop mode (38)
CMD_VIDEO_RANDOM = 0x27     # Video random mode (39)
CMD_ROTATION = 0x28         # Picture rotation angle (40)
CMD_LANGUAGE = 0x29         # Set language (41)


# ── Command Builders ──────────────────────────────────────────────────


def brightness(level: int) -> Message:
    """Set LCD brightness (0-100)."""
    level = max(0, min(100, level))
    return Message(cmd=CMD_BRIGHTNESS, payload=bytes([0x00, level]))


def screen_power(on: bool) -> Message:
    """Turn LCD screen on (1) or off (0)."""
    return Message(cmd=CMD_SCREEN, payload=bytes([1 if on else 0]))


def rotation(angle: int) -> Message:
    """Set LCD rotation (0, 90, 180, 270).

    Angle index: 0=0°, 1=90°, 2=180°, 3=270°.
    """
    index = {0: 0, 90: 1, 180: 2, 270: 3}.get(angle, 0)
    return Message(cmd=CMD_ROTATION, payload=bytes([index]))


def video_loop(enable: bool) -> Message:
    """Enable/disable video loop mode."""
    return Message(cmd=CMD_VIDEO_LOOP, payload=bytes([1 if enable else 0]))


def video_random(enable: bool) -> Message:
    """Enable/disable video random playback."""
    return Message(cmd=CMD_VIDEO_RANDOM, payload=bytes([1 if enable else 0]))


def language(lang_id: int) -> Message:
    """Set device UI language (0=Chinese, 1=English, etc.)."""
    return Message(cmd=CMD_LANGUAGE, payload=bytes([lang_id]))


def sensor_data(
    *,
    cpu_surface_temp: int = 0,
    cpu_core_temp: int = 0,
    cpu_package_temp: int = 0,
    cpu_voltage_mv: int = 0,
    cpu_power: int = 0,
    cpu_usage: int = 0,
    cpu_speed_mhz: int = 0,
    memory_usage: int = 0,
    gpu_temp: int = 0,
    gpu_load: int = 0,
    gpu_freq_mhz: int = 0,
    fan_rpm: int = 0,
) -> Message:
    """Push sensor readings to the device LCD overlay.

    Matches Set_FanData_org() from C# — packs 13 sensor values into
    a 38-byte payload using uint16 LE encoding.
    """
    payload = bytearray()
    payload += pack_uint16_le(cpu_surface_temp)
    payload += pack_uint16_le(cpu_core_temp)
    payload += pack_uint16_le(cpu_package_temp)
    # Voltage is 3 bytes in C# (lo, hi>>8, hi>>16) — pack as LE uint16 + extra byte
    payload += struct.pack("<I", cpu_voltage_mv)[:3]
    payload += pack_uint16_le(cpu_power)
    payload += pack_uint16_le(cpu_usage)
    payload += pack_uint16_le(memory_usage)
    payload += pack_uint16_le(cpu_speed_mhz)
    # 4 bytes padding (C# packs uint32 zero)
    payload += b"\x00\x00\x00\x00"
    payload += pack_uint16_le(gpu_temp)
    payload += pack_uint16_le(gpu_load)
    payload += pack_uint16_le(gpu_freq_mhz)
    # 2 bytes padding
    payload += b"\x00\x00"
    payload += pack_uint16_le(fan_rpm)

    return Message(cmd=CMD_SENSOR_DATA, payload=bytes(payload))


def file_notice(filename: str) -> Message:
    """Notify device about an image/video file (after ADB push).

    Filename is UTF-8 encoded, padded to 32 bytes.
    """
    name_bytes = filename.encode("utf-8")[:32]
    padded = name_bytes.ljust(32, b"\x00")
    return Message(cmd=CMD_FILE_NOTICE, payload=padded)


def set_background(
    *,
    bg_type: int = 0,
    show_data: int = 1,
    unit: str = "°C",
    filename: str = "00.png",
) -> Message:
    """Set the background image displayed on the LCD.

    Args:
        bg_type: 0=image, 1=color, etc.
        show_data: 1=show sensor overlay, 0=hide
        unit: Temperature unit string (max 3 bytes)
        filename: Background image filename (max 32 bytes)
    """
    payload = bytearray()
    payload += bytes([bg_type])
    payload += pack_uint16_le(show_data)
    # Unit: 3 bytes, padded
    unit_bytes = unit.encode("utf-8")[:3]
    payload += unit_bytes.ljust(3, b"\x00")
    # Filename: 32 bytes, padded
    name_bytes = filename.encode("utf-8")[:32]
    payload += name_bytes.ljust(32, b"\x00")
    return Message(cmd=CMD_BACKGROUND, payload=bytes(payload))


# ── RGB565 Conversion ─────────────────────────────────────────────────


def image_to_rgb565(img: object) -> bytes:
    """Convert a PIL Image to RGB565 bytes for LCD display.

    The device expects raw RGB565 (16-bit per pixel, little-endian)
    at the native LCD resolution (typically 480x480).

    Args:
        img: PIL.Image.Image in RGB mode

    Returns:
        Raw RGB565 bytes (width * height * 2 bytes)
    """
    from PIL import Image

    if not isinstance(img, Image.Image):
        raise TypeError(f"Expected PIL Image, got {type(img).__name__}")

    rgb = img.convert("RGB")
    pixels = rgb.tobytes()  # RGBRGBRGB...

    # Convert RGB888 to RGB565 LE
    out = bytearray(rgb.width * rgb.height * 2)
    for i in range(0, len(pixels), 3):
        r, g, b = pixels[i], pixels[i + 1], pixels[i + 2]
        # RGB565: RRRR RGGG GGGB BBBB
        pixel = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
        j = (i // 3) * 2
        out[j] = pixel & 0xFF       # low byte
        out[j + 1] = pixel >> 8     # high byte

    return bytes(out)


def image_to_rgb565_numpy(img: object) -> bytes:
    """Fast RGB565 conversion using numpy (preferred when available)."""
    import numpy as np
    from PIL import Image

    if not isinstance(img, Image.Image):
        raise TypeError(f"Expected PIL Image, got {type(img).__name__}")

    rgb = np.array(img.convert("RGB"), dtype=np.uint16)
    r = rgb[:, :, 0]
    g = rgb[:, :, 1]
    b = rgb[:, :, 2]
    rgb565 = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
    return rgb565.astype("<u2").tobytes()
