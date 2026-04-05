"""DevicePort implementation — combines ADB + TCP for full device communication.

Connection flow (from decompiled C#):
1. ADB discovers device IP
2. ADB connects to device
3. ADB sets up port forward (local → device TCP port)
4. TCP client connects to 127.0.0.1:forwarded_port
5. Messages sent/received via TCP
6. Files pushed via ADB push

Implements DevicePort ABC from core/ports.py.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from trcc_vision.core.ports import DevicePort
from trcc_vision.protocols.adb import ADBProtocol
from trcc_vision.protocols.tcp_client import TCPClient

if TYPE_CHECKING:
    from trcc_vision.core.models import DeviceInfo
    from trcc_vision.protocols.message import Message

log = logging.getLogger(__name__)

DEFAULT_ADB_PORT = 5555
DEFAULT_TCP_PORT = 5037  # typical Android debug port
LOCAL_FORWARD_PORT = 15037  # local side of ADB forward


class DeviceProtocol(DevicePort):
    """Full device communication via ADB + TCP.

    Usage:
        proto = DeviceProtocol()
        proto.connect(device_info)
        response = proto.send_command(some_message.serialize())
        proto.send_frame(rgb565_bytes, 480, 480)
        proto.disconnect()
    """

    def __init__(
        self,
        adb: ADBProtocol | None = None,
        tcp: TCPClient | None = None,
    ) -> None:
        self._adb = adb or ADBProtocol()
        self._tcp = tcp or TCPClient()
        self._device: DeviceInfo | None = None

    def connect(self, device: DeviceInfo) -> None:
        """Establish ADB + TCP connection to device."""
        log.info("Connecting to device: %s (%s)", device.name, device.address)

        # Parse host:port from address
        host, port = self._parse_address(device.address)

        # ADB connect (for network devices)
        if ":" in device.address or "." in device.address:
            self._adb.connect(host, port)

        # Set up port forward so TCP goes through ADB
        self._adb.forward(LOCAL_FORWARD_PORT, DEFAULT_TCP_PORT)

        # TCP connect to forwarded port
        self._tcp.connect("127.0.0.1", LOCAL_FORWARD_PORT)

        self._device = device
        log.info("Device connected: %s", device.name)

    def disconnect(self) -> None:
        """Clean disconnect from device."""
        log.info("Disconnecting from device...")
        self._tcp.disconnect()
        if self._device:
            host, port = self._parse_address(self._device.address)
            try:
                self._adb.disconnect(host, port)
            except Exception:
                log.debug("ADB disconnect cleanup failed (non-fatal)")
        self._device = None
        log.info("Device disconnected")

    def is_connected(self) -> bool:
        """Check if both ADB and TCP are alive."""
        return self._device is not None and self._tcp.is_connected

    def send_frame(self, data: bytes, width: int, height: int) -> None:
        """Send an LCD frame to the device.

        For large frames, this uses ADB push to a temp file on the device.
        For small data, this could use TCP. Current implementation uses TCP.
        """
        log.debug("send_frame: %d bytes, %dx%d", len(data), width, height)
        if not self.is_connected():
            raise ConnectionError("Device not connected")

        # TODO: determine if frame should go via TCP or ADB push
        # For now, send via TCP
        self._tcp.send_raw(data)
        log.debug("Frame sent: %d bytes", len(data))

    def send_command(self, cmd: bytes) -> bytes:
        """Send a raw command via TCP and return the response."""
        log.debug("send_command: %d bytes [%s]", len(cmd), cmd[:16].hex())
        if not self.is_connected():
            raise ConnectionError("Device not connected")
        return self._tcp.send_raw(cmd)

    def send_message(self, msg: Message) -> bytes:
        """Send a protocol Message and return the response."""
        log.debug("send_message: cmd=0x%02X", msg.cmd)
        return self._tcp.send_message(msg)

    def push_file(self, local_path: str, remote_path: str) -> bool:
        """Push a file to the device via ADB."""
        log.info("Pushing file: %s → %s", local_path, remote_path)
        return self._adb.push(local_path, remote_path)

    def shell(self, cmd: str) -> str:
        """Execute a shell command on the device via ADB."""
        log.debug("Shell command: %s", cmd)
        return self._adb.shell(cmd)

    def _parse_address(self, address: str) -> tuple[str, int]:
        """Parse 'host:port' or just 'host' from device address."""
        if ":" in address:
            parts = address.rsplit(":", 1)
            try:
                return parts[0], int(parts[1])
            except ValueError:
                return address, DEFAULT_ADB_PORT
        return address, DEFAULT_ADB_PORT
