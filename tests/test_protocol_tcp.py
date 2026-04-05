"""Tests for TCP client — uses socket mocking, no real connections."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from trcc_vision.protocols.message import Message
from trcc_vision.protocols.tcp_client import TCPClient, TCPClientError


@pytest.fixture()
def tcp() -> TCPClient:
    """TCP client with short timeout for tests."""
    return TCPClient(timeout=1.0)


@pytest.fixture()
def mock_socket() -> MagicMock:
    """Pre-configured mock socket."""
    sock = MagicMock()
    sock.recv.return_value = bytes([0xAA, 0xF5, 0x01, 0x00, 0x00, 0x01])
    return sock


class TestTCPConnect:
    def test_connect_creates_socket(self, tcp: TCPClient) -> None:
        with patch("trcc_vision.protocols.tcp_client.socket.socket") as mock_cls:
            mock_sock = MagicMock()
            mock_cls.return_value = mock_sock
            tcp.connect("127.0.0.1", 5037)
            mock_sock.connect.assert_called_once_with(("127.0.0.1", 5037))

    def test_connect_failure_raises(self, tcp: TCPClient) -> None:
        with patch("trcc_vision.protocols.tcp_client.socket.socket") as mock_cls:
            mock_sock = MagicMock()
            mock_sock.connect.side_effect = OSError("refused")
            mock_cls.return_value = mock_sock
            with pytest.raises(TCPClientError, match="Failed to connect"):
                tcp.connect("127.0.0.1", 9999)

    def test_is_connected_false_initially(self, tcp: TCPClient) -> None:
        assert tcp.is_connected is False


class TestTCPSendReceive:
    def test_send_raw(self, tcp: TCPClient, mock_socket: MagicMock) -> None:
        tcp._sock = mock_socket
        tcp._host = "127.0.0.1"
        tcp._port = 5037
        response = tcp.send_raw(bytes([0x01, 0x02]))
        mock_socket.sendall.assert_called_once_with(bytes([0x01, 0x02]))
        assert len(response) > 0

    def test_send_message(self, tcp: TCPClient, mock_socket: MagicMock) -> None:
        tcp._sock = mock_socket
        tcp._host = "127.0.0.1"
        tcp._port = 5037
        msg = Message(cmd=0x01, payload=b"", serial=1)
        response = tcp.send_message(msg)
        assert mock_socket.sendall.called
        assert len(response) > 0

    def test_send_when_disconnected_raises(self, tcp: TCPClient) -> None:
        with pytest.raises(TCPClientError, match="Not connected"):
            tcp.send_raw(b"\x00")


class TestTCPDisconnect:
    def test_disconnect_closes_socket(
        self, tcp: TCPClient, mock_socket: MagicMock,
    ) -> None:
        tcp._sock = mock_socket
        tcp._host = "127.0.0.1"
        tcp._port = 5037
        tcp.disconnect()
        mock_socket.shutdown.assert_called_once()
        mock_socket.close.assert_called_once()
        assert tcp._sock is None

    def test_disconnect_when_already_disconnected(self, tcp: TCPClient) -> None:
        tcp.disconnect()  # should not raise


class TestTCPReconnect:
    def test_reconnects_on_send_failure(
        self, tcp: TCPClient, mock_socket: MagicMock,
    ) -> None:
        tcp._sock = mock_socket
        tcp._host = "127.0.0.1"
        tcp._port = 5037

        # First sendall fails, triggering reconnect
        call_count = 0

        def side_effect(data: bytes) -> None:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise OSError(10057, "Not connected")

        mock_socket.sendall.side_effect = side_effect

        with patch("trcc_vision.protocols.tcp_client.socket.socket") as mock_cls:
            new_sock = MagicMock()
            new_sock.recv.return_value = bytes([0xAA, 0xF5, 0x00, 0x00, 0x00, 0x00])
            mock_cls.return_value = new_sock
            response = tcp.send_raw(b"\x01")
            assert len(response) > 0
