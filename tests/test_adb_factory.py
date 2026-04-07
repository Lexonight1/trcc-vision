"""Tests for ADB adapter factory — verifies platform dispatch and fallback."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from trcc_vision.infrastructure.platform import Platform
from trcc_vision.protocols.adb import ADBError, ADBPort
from trcc_vision.protocols.adb_factory import NullADBPort, create_adb_port

# ── Factory dispatch ───────────────────────────────────────────────────


class TestCreateAdbPort:
    """Factory returns the correct adapter for each platform."""

    @patch("trcc_vision.protocols.adb_factory.current_platform")
    def test_linux_returns_linux_adapter(self, mock_platform) -> None:
        mock_platform.return_value = Platform.LINUX
        port = create_adb_port()
        from trcc_vision.protocols.adb_linux import LinuxADBAdapter
        assert isinstance(port, LinuxADBAdapter)

    @patch("trcc_vision.protocols.adb_factory.current_platform")
    def test_macos_returns_macos_adapter(self, mock_platform) -> None:
        mock_platform.return_value = Platform.MACOS
        port = create_adb_port()
        from trcc_vision.protocols.adb_macos import MacOSADBAdapter
        assert isinstance(port, MacOSADBAdapter)

    @patch("trcc_vision.protocols.adb_factory.current_platform")
    def test_windows_returns_windows_adapter(self, mock_platform) -> None:
        mock_platform.return_value = Platform.WINDOWS
        port = create_adb_port()
        from trcc_vision.protocols.adb_windows import WindowsADBAdapter
        assert isinstance(port, WindowsADBAdapter)

    @patch("trcc_vision.protocols.adb_factory.current_platform")
    def test_bsd_returns_bsd_adapter(self, mock_platform) -> None:
        mock_platform.return_value = Platform.BSD
        port = create_adb_port()
        from trcc_vision.protocols.adb_bsd import BSDADBAdapter
        assert isinstance(port, BSDADBAdapter)

    @patch("trcc_vision.protocols.adb_factory.current_platform")
    def test_unknown_returns_null_port(self, mock_platform) -> None:
        mock_platform.return_value = Platform.UNKNOWN
        port = create_adb_port()
        assert isinstance(port, NullADBPort)

    def test_all_adapters_implement_adb_port(self) -> None:
        """Sanity check: all concrete adapters are ADBPort subclasses."""
        from trcc_vision.protocols.adb_bsd import BSDADBAdapter
        from trcc_vision.protocols.adb_linux import LinuxADBAdapter
        from trcc_vision.protocols.adb_macos import MacOSADBAdapter
        from trcc_vision.protocols.adb_windows import WindowsADBAdapter

        for cls in (
            LinuxADBAdapter, MacOSADBAdapter, WindowsADBAdapter,
            BSDADBAdapter, NullADBPort,
        ):
            assert issubclass(cls, ADBPort)


# ── NullADBPort behavior ──────────────────────────────────────────────


class TestNullADBPort:
    """NullADBPort gracefully reports ADB as unavailable."""

    def test_is_not_available(self) -> None:
        assert NullADBPort().is_available() is False

    def test_devices_empty(self) -> None:
        assert NullADBPort().devices() == []

    def test_connect_fails(self) -> None:
        assert NullADBPort().connect("192.168.1.100") is False

    def test_push_fails(self) -> None:
        assert NullADBPort().push("/tmp/a", "/sdcard/b") is False

    def test_forward_fails(self) -> None:
        assert NullADBPort().forward(15037, 5037) is False

    def test_shell_raises(self) -> None:
        with pytest.raises(ADBError, match="not available"):
            NullADBPort().shell("echo hi")

    def test_get_version_none(self) -> None:
        assert NullADBPort().get_version() is None

    def test_disconnect_noop(self) -> None:
        NullADBPort().disconnect()  # should not raise
