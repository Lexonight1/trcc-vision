"""TCP socket client — sends/receives framed messages to TR-VISION device.

Matches the C# AsyncTCPClient behavior:
- Connects to 127.0.0.1 (via ADB port forward) or device IP
- 1024-byte receive buffer
- Handles error codes 10057 (not connected) and 10053 (connection aborted)
- Synchronous send/receive with reconnect on failure

Derived from decompiled AsyncTCPClient.cs.
"""

from __future__ import annotations

import logging
import socket
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trcc_vision.protocols.message import Message

log = logging.getLogger(__name__)

RECV_BUFFER_SIZE = 1024
DEFAULT_TIMEOUT = 3.0  # seconds


class TCPClientError(Exception):
    """Raised on TCP communication failure."""


class TCPClient:
    """Synchronous TCP client for TR-VISION device communication.

    Usage:
        client = TCPClient()
        client.connect("127.0.0.1", 5037)
        response = client.send(some_message)
        client.disconnect()
    """

    def __init__(self, timeout: float = DEFAULT_TIMEOUT) -> None:
        self._sock: socket.socket | None = None
        self._timeout = timeout
        self._host: str = ""
        self._port: int = 0

    @property
    def is_connected(self) -> bool:
        """Check if the socket is alive."""
        if self._sock is None:
            return False
        try:
            # Peek with zero-length recv to test connection
            self._sock.setblocking(False)
            try:
                self._sock.recv(0)
            except BlockingIOError:
                return True  # no data but connection alive
            except OSError:
                return False
            finally:
                self._sock.setblocking(True)
            return True
        except OSError:
            return False

    def connect(self, host: str, port: int) -> None:
        """Establish TCP connection to device."""
        log.info("TCP connecting to %s:%d...", host, port)
        self._host = host
        self._port = port

        self._sock = socket.socket(
            socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP,
        )
        self._sock.settimeout(self._timeout)

        try:
            self._sock.connect((host, port))
            log.info("TCP connected to %s:%d", host, port)
        except OSError as e:
            log.error("TCP connect failed: %s:%d — %s", host, port, e)
            self._close_socket()
            raise TCPClientError(f"Failed to connect to {host}:{port}") from e

    def disconnect(self) -> None:
        """Cleanly shut down the TCP connection."""
        if self._sock:
            log.info("TCP disconnecting from %s:%d", self._host, self._port)
            self._close_socket()
        else:
            log.debug("TCP already disconnected")

    def send_raw(self, data: bytes) -> bytes:
        """Send raw bytes and return the response.

        Reconnects automatically on connection reset (matching C# behavior).
        """
        if not self._sock:
            raise TCPClientError("Not connected")

        log.debug("TCP send: %d bytes [%s]", len(data), data[:32].hex())
        try:
            self._sock.sendall(data)
            response = self._sock.recv(RECV_BUFFER_SIZE)
            log.debug("TCP recv: %d bytes [%s]", len(response), response[:32].hex())
            return response
        except OSError as e:
            errno = getattr(e, "errno", 0) or 0
            log.warning(
                "TCP send/recv failed (errno=%d): %s — reconnecting",
                errno, e,
            )
            # Reconnect on failure (matching C# error codes 10057/10053)
            self._reconnect()
            # Retry once after reconnect
            try:
                self._sock.sendall(data)  # type: ignore[union-attr]
                response = self._sock.recv(RECV_BUFFER_SIZE)  # type: ignore[union-attr]
                log.debug("TCP recv (retry): %d bytes", len(response))
                return response
            except OSError as e2:
                log.error("TCP retry failed: %s", e2)
                raise TCPClientError(f"Send failed after reconnect: {e2}") from e2

    def send_message(self, msg: Message) -> bytes:
        """Serialize a Message and send it, return raw response bytes."""
        return self.send_raw(msg.serialize())

    def _reconnect(self) -> None:
        """Close and re-establish the connection."""
        log.info("TCP reconnecting to %s:%d...", self._host, self._port)
        self._close_socket()
        try:
            self.connect(self._host, self._port)
        except TCPClientError:
            log.error("TCP reconnect failed")

    def _close_socket(self) -> None:
        """Safely close the socket."""
        import contextlib

        if self._sock:
            with contextlib.suppress(OSError):
                self._sock.shutdown(socket.SHUT_RDWR)
            with contextlib.suppress(OSError):
                self._sock.close()
            self._sock = None
            log.debug("TCP socket closed")
