"""Tests for TR-VISION message protocol — framing, checksum, serialization."""

from __future__ import annotations

from trcc_vision.protocols.message import (
    HEADER,
    Message,
    MessageType,
    checksum_sum,
    checksum_xor,
    pack_uint16_le,
    pack_uint32_le,
    unpack_uint16_be,
    unpack_uint16_le,
    unpack_uint32_be,
    unpack_uint32_le,
)

# ── Checksum ────────────────────────────────────────────────────────────


class TestChecksum:
    def test_sum_empty(self) -> None:
        assert checksum_sum(b"") == 0

    def test_sum_single(self) -> None:
        assert checksum_sum(bytes([0xFF])) == 0xFF

    def test_sum_wraps_at_256(self) -> None:
        # 0x80 + 0x80 = 0x100 → wraps to 0x00
        assert checksum_sum(bytes([0x80, 0x80])) == 0x00

    def test_sum_known_value(self) -> None:
        # 1 + 2 + 3 + 4 = 10
        assert checksum_sum(bytes([1, 2, 3, 4])) == 10

    def test_xor_empty(self) -> None:
        assert checksum_xor(b"") == 0

    def test_xor_cancels_same_bytes(self) -> None:
        assert checksum_xor(bytes([0xAB, 0xAB])) == 0

    def test_xor_known_value(self) -> None:
        assert checksum_xor(bytes([0x0F, 0xF0])) == 0xFF


# ── Byte Order ──────────────────────────────────────────────────────────


class TestByteOrder:
    def test_pack_unpack_uint16_le(self) -> None:
        raw = pack_uint16_le(0x1234)
        assert raw == bytes([0x34, 0x12])
        assert unpack_uint16_le(raw) == 0x1234

    def test_pack_unpack_uint32_le(self) -> None:
        raw = pack_uint32_le(0xDEADBEEF)
        assert raw == bytes([0xEF, 0xBE, 0xAD, 0xDE])
        assert unpack_uint32_le(raw) == 0xDEADBEEF

    def test_unpack_uint16_be(self) -> None:
        assert unpack_uint16_be(bytes([0x12, 0x34])) == 0x1234

    def test_unpack_uint32_be(self) -> None:
        assert unpack_uint32_be(bytes([0xDE, 0xAD, 0xBE, 0xEF])) == 0xDEADBEEF

    def test_offset(self) -> None:
        data = bytes([0x00, 0x00, 0x34, 0x12])
        assert unpack_uint16_le(data, offset=2) == 0x1234


# ── Message Serialization ──────────────────────────────────────────────


class TestMessageSerialize:
    def test_header_present(self) -> None:
        msg = Message(cmd=0x01)
        raw = msg.serialize()
        assert raw[:2] == HEADER

    def test_serial_in_bytes_3_4(self) -> None:
        msg = Message(cmd=0x01, serial=42)
        raw = msg.serialize()
        assert unpack_uint16_le(raw, 2) == 42

    def test_cmd_at_byte_4(self) -> None:
        msg = Message(cmd=0x3A, serial=1)
        raw = msg.serialize()
        assert raw[4] == 0x3A

    def test_payload_follows_cmd(self) -> None:
        payload = bytes([0x10, 0x20, 0x30])
        msg = Message(cmd=0x01, payload=payload, serial=1)
        raw = msg.serialize()
        assert raw[5:8] == payload

    def test_checksum_is_last_byte(self) -> None:
        msg = Message(cmd=0x01, payload=b"", serial=1)
        raw = msg.serialize()
        body = raw[2:-1]  # between header and checksum
        assert raw[-1] == checksum_sum(body)

    def test_minimum_message_length(self) -> None:
        # header(2) + serial(2) + cmd(1) + checksum(1) = 6
        msg = Message(cmd=0x00, payload=b"", serial=0)
        assert len(msg.serialize()) == 6


# ── Message Parsing ─────────────────────────────────────────────────────


class TestMessageParse:
    def test_roundtrip(self) -> None:
        original = Message(cmd=0x3A, payload=bytes([0x01, 0x02, 0x03]), serial=100)
        raw = original.serialize()
        parsed = Message.parse(raw)
        assert parsed is not None
        assert parsed.cmd == 0x3A
        assert parsed.payload == bytes([0x01, 0x02, 0x03])
        assert parsed.serial == 100

    def test_too_short_returns_none(self) -> None:
        assert Message.parse(bytes([0xAA, 0xF5, 0x00])) is None

    def test_bad_header_returns_none(self) -> None:
        assert Message.parse(bytes([0x00, 0x00, 0x01, 0x00, 0x00, 0x01])) is None

    def test_bad_checksum_returns_none(self) -> None:
        msg = Message(cmd=0x01, serial=1)
        raw = bytearray(msg.serialize())
        raw[-1] ^= 0xFF  # corrupt checksum
        assert Message.parse(bytes(raw)) is None

    def test_empty_payload(self) -> None:
        msg = Message(cmd=0x00, payload=b"", serial=0)
        raw = msg.serialize()
        parsed = Message.parse(raw)
        assert parsed is not None
        assert parsed.payload == b""


# ── Message Types ───────────────────────────────────────────────────────


class TestMessageTypes:
    def test_set_param_length(self) -> None:
        assert MessageType.SET_PARAM == 81

    def test_set_realtime_length(self) -> None:
        assert MessageType.SET_REALTIME == 10

    def test_no_data_cmd_length(self) -> None:
        assert MessageType.NO_DATA_CMD == 7


# ── Hex Dump ────────────────────────────────────────────────────────────


class TestHexDump:
    def test_format(self) -> None:
        msg = Message(cmd=0x01, payload=b"", serial=0)
        dump = msg.hex_dump()
        assert "AA" in dump
        assert "F5" in dump
        assert " " in dump  # space-separated
