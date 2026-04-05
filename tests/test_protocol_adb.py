"""Tests for ADB protocol wrapper — uses subprocess mocking, no real ADB."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from trcc_vision.protocols.adb import ADBDevice, ADBError, ADBProtocol


@pytest.fixture()
def adb() -> ADBProtocol:
    """ADB protocol with a known binary path."""
    return ADBProtocol(adb_path="/usr/bin/adb")


class TestADBDevices:
    def test_parses_device_list(self, adb: ADBProtocol) -> None:
        fake_output = (
            "List of devices attached\n"
            "192.168.1.100:5555\tdevice\n"
            "ABCD1234\toffline\n"
        )
        with patch.object(adb, "_run", return_value=fake_output):
            devices = adb.devices()
        assert len(devices) == 2
        assert devices[0] == ADBDevice(serial="192.168.1.100:5555", state="device")
        assert devices[1] == ADBDevice(serial="ABCD1234", state="offline")

    def test_empty_device_list(self, adb: ADBProtocol) -> None:
        with patch.object(adb, "_run", return_value="List of devices attached\n"):
            devices = adb.devices()
        assert devices == []


class TestADBConnect:
    def test_successful_connect(self, adb: ADBProtocol) -> None:
        with patch.object(adb, "_run", return_value="connected to 192.168.1.100:5555"):
            assert adb.connect("192.168.1.100", 5555) is True

    def test_already_connected(self, adb: ADBProtocol) -> None:
        with patch.object(adb, "_run", return_value="already connected to 192.168.1.100:5555"):
            assert adb.connect("192.168.1.100", 5555) is True

    def test_failed_connect(self, adb: ADBProtocol) -> None:
        with patch.object(adb, "_run", side_effect=ADBError("connection refused")):
            assert adb.connect("10.0.0.1", 5555) is False


class TestADBPush:
    def test_successful_push(self, adb: ADBProtocol) -> None:
        with patch.object(adb, "_run", return_value="1 file pushed"):
            assert adb.push("/tmp/image.png", "/sdcard/00.png") is True

    def test_failed_push(self, adb: ADBProtocol) -> None:
        with patch.object(adb, "_run", side_effect=ADBError("device not found")):
            assert adb.push("/tmp/image.png", "/sdcard/00.png") is False


class TestADBShell:
    def test_returns_output(self, adb: ADBProtocol) -> None:
        with patch.object(adb, "_run", return_value="12"):
            result = adb.shell("getprop ro.build.version.sdk")
        assert result == "12"


class TestADBForward:
    def test_successful_forward(self, adb: ADBProtocol) -> None:
        with patch.object(adb, "_run", return_value=""):
            assert adb.forward(15037, 5037) is True

    def test_failed_forward(self, adb: ADBProtocol) -> None:
        with patch.object(adb, "_run", side_effect=ADBError("error")):
            assert adb.forward(15037, 5037) is False


class TestADBAvailability:
    def test_version(self, adb: ADBProtocol) -> None:
        with patch.object(adb, "_run", return_value="Android Debug Bridge version 1.0.41"):
            ver = adb.get_version()
        assert ver is not None
        assert "Android Debug Bridge" in ver

    def test_is_available_true(self) -> None:
        with patch("trcc_vision.protocols.adb.shutil.which", return_value="/usr/bin/adb"):
            adb = ADBProtocol()
            assert adb.is_available() is True

    def test_is_available_false(self) -> None:
        with patch("trcc_vision.protocols.adb.shutil.which", return_value=None):
            adb = ADBProtocol(adb_path="nonexistent")
            assert adb.is_available() is False
