"""TR-VISION message protocol — framing, checksum, serialization.

All messages use the format:
    [0xAA] [0xF5] [serial_lo] [serial_hi] [cmd] [payload...] [checksum]

Derived from decompiled MsgHelper.cs / DataHandle.cs.
"""

from __future__ import annotations

import logging
import struct
from dataclasses import dataclass, field
from enum import IntEnum

log = logging.getLogger(__name__)

HEADER = bytes([0xAA, 0xF5])
SERIAL_MAX = 65536

# Global serial counter (wraps at 65536, matching C# GetserialNumber)
_serial_counter = 0


def _next_serial() -> int:
    """Get next serial number, wrapping at 65536."""
    global _serial_counter  # noqa: PLW0603
    _serial_counter = (_serial_counter + 1) % SERIAL_MAX
    return _serial_counter


def checksum_sum(data: bytes) -> int:
    """Additive checksum — sum all bytes, return lowest 8 bits.

    Matches C# DataHandle.CheckSum().
    """
    return sum(data) & 0xFF


def checksum_xor(data: bytes) -> int:
    """XOR checksum — XOR all bytes.

    Matches C# DataHandle.CheckSum_Xor().
    """
    result = 0
    for b in data:
        result ^= b
    return result


# ── Byte Order Helpers (matching C# DataHandle) ────────────────────────


def pack_uint16_le(value: int) -> bytes:
    """Pack unsigned 16-bit integer, little-endian."""
    return struct.pack("<H", value & 0xFFFF)


def pack_uint32_le(value: int) -> bytes:
    """Pack unsigned 32-bit integer, little-endian."""
    return struct.pack("<I", value & 0xFFFFFFFF)


def unpack_uint16_le(data: bytes, offset: int = 0) -> int:
    """Unpack unsigned 16-bit integer, little-endian."""
    return struct.unpack_from("<H", data, offset)[0]


def unpack_uint32_le(data: bytes, offset: int = 0) -> int:
    """Unpack unsigned 32-bit integer, little-endian."""
    return struct.unpack_from("<I", data, offset)[0]


def unpack_uint16_be(data: bytes, offset: int = 0) -> int:
    """Unpack unsigned 16-bit integer, big-endian."""
    return struct.unpack_from(">H", data, offset)[0]


def unpack_uint32_be(data: bytes, offset: int = 0) -> int:
    """Unpack unsigned 32-bit integer, big-endian."""
    return struct.unpack_from(">I", data, offset)[0]


# ── Message Types ───────────────────────────────────────────────────────


class MessageType(IntEnum):
    """Known message types and their total byte lengths (from MsgHelper.cs)."""

    SET_PARAM = 81        # GetSetParmMsg — configuration settings
    SET_REALTIME = 10     # GetSetRealTimeParmMsg — sensor data push
    SET_BIOS = 21         # GetSetBiosParmMsg — BIOS parameters
    FILE_NOTICE = 39      # GetPushOrDelFileNoticeMsg — file operations
    PUSH_BG_DONE = 42     # GetFinishedPushBgPicNoticeMsg — background push ack
    SET_SYS_PARAM = 8     # GetSetSysParamMsg — system parameters
    NO_DATA_CMD = 7       # GetNoDataCmdMsg — command with no payload


# ── Message ─────────────────────────────────────────────────────────────


@dataclass
class Message:
    """A single protocol message.

    Build outgoing:
        msg = Message(cmd=0x01, payload=bytes([0x00, 0x01]))
        raw = msg.serialize()

    Parse incoming:
        msg = Message.parse(raw_bytes)
    """

    cmd: int
    payload: bytes = b""
    serial: int = field(default_factory=_next_serial)

    def serialize(self) -> bytes:
        """Serialize to wire format: header + serial + cmd + payload + checksum."""
        body = (
            pack_uint16_le(self.serial)
            + bytes([self.cmd])
            + self.payload
        )
        chk = checksum_sum(body)
        raw = HEADER + body + bytes([chk])
        log.debug(
            "Serialize: cmd=0x%02X serial=%d len=%d checksum=0x%02X",
            self.cmd, self.serial, len(raw), chk,
        )
        return raw

    @classmethod
    def parse(cls, data: bytes) -> Message | None:
        """Parse a message from raw bytes. Returns None if invalid."""
        if len(data) < 5:
            log.warning("Message too short: %d bytes", len(data))
            return None

        if data[0:2] != HEADER:
            log.warning(
                "Invalid header: expected AA F5, got %02X %02X",
                data[0], data[1],
            )
            return None

        serial = unpack_uint16_le(data, 2)
        cmd = data[4]
        payload = data[5:-1]
        received_chk = data[-1]

        # Verify checksum over body (everything between header and checksum)
        body = data[2:-1]
        expected_chk = checksum_sum(body)
        if received_chk != expected_chk:
            log.warning(
                "Checksum mismatch: expected 0x%02X, got 0x%02X",
                expected_chk, received_chk,
            )
            return None

        msg = cls(cmd=cmd, payload=payload, serial=serial)
        log.debug(
            "Parsed: cmd=0x%02X serial=%d payload=%d bytes",
            cmd, serial, len(payload),
        )
        return msg

    def hex_dump(self) -> str:
        """Format serialized bytes as hex string for logging."""
        raw = self.serialize()
        return " ".join(f"{b:02X}" for b in raw)
