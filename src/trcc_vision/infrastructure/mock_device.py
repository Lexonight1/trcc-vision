"""Mock device port — simulates a TR-VISION device for development without hardware.

Implements DevicePort with:
- Connection state tracking
- Frame capture (stores last frame for GUI preview)
- Canned protocol responses matching 0xAA F5 format
- Fake device info for detection

Activate via: trcc-vision --mock detect
"""

from __future__ import annotations

import logging
import time

from trcc_vision.core.enums import ConnectionType
from trcc_vision.core.models import DeviceInfo
from trcc_vision.core.ports import DevicePort
from trcc_vision.protocols.message import HEADER, checksum_sum, pack_uint16_le

log = logging.getLogger(__name__)

MOCK_DEVICE = DeviceInfo(
    name="TR-VISION Mock",
    connection=ConnectionType.ADB,
    address="127.0.0.1:5555",
    lcd_width=480,
    lcd_height=480,
)


class MockDevicePort(DevicePort):
    """Fake DevicePort that simulates a TR-VISION device in memory."""

    def __init__(self) -> None:
        self._connected = False
        self._last_frame: bytes | None = None
        self._last_frame_size: tuple[int, int] = (0, 0)
        self._frame_count = 0
        self._brightness = 100
        self._connect_time: float = 0.0
        log.info("MockDevicePort created — no real hardware")

    def connect(self, device: DeviceInfo) -> None:
        """Simulate device connection."""
        log.info("Mock connect: %s (%s)", device.name, device.address)
        self._connected = True
        self._connect_time = time.time()

    def disconnect(self) -> None:
        """Simulate device disconnection."""
        log.info("Mock disconnect (was connected %.1fs)", time.time() - self._connect_time)
        self._connected = False
        self._last_frame = None
        self._frame_count = 0

    def is_connected(self) -> bool:
        return self._connected

    def send_frame(self, data: bytes, width: int, height: int) -> None:
        """Accept frame data — store for GUI preview."""
        if not self._connected:
            raise ConnectionError("Mock device not connected")
        self._last_frame = data
        self._last_frame_size = (width, height)
        self._frame_count += 1
        log.debug(
            "Mock frame #%d: %d bytes, %dx%d",
            self._frame_count, len(data), width, height,
        )

    def send_command(self, cmd: bytes) -> bytes:
        """Return a canned response in protocol format."""
        if not self._connected:
            raise ConnectionError("Mock device not connected")
        log.debug("Mock command: %d bytes [%s]", len(cmd), cmd[:16].hex())
        return self._build_ack(cmd)

    @property
    def last_frame(self) -> bytes | None:
        """Last frame sent (for GUI preview display)."""
        return self._last_frame

    @property
    def last_frame_size(self) -> tuple[int, int]:
        """Width, height of the last frame."""
        return self._last_frame_size

    @property
    def frame_count(self) -> int:
        """Total frames sent since connect."""
        return self._frame_count

    def _build_ack(self, cmd: bytes) -> bytes:
        """Build a mock acknowledgement response."""
        # Echo back the command byte with 0x00 status (success)
        cmd_byte = cmd[4] if len(cmd) > 4 else 0x00
        body = pack_uint16_le(0) + bytes([cmd_byte, 0x00])
        chk = checksum_sum(body)
        return HEADER + body + bytes([chk])
