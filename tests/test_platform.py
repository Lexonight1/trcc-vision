"""Tests for cross-platform path resolution."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from trcc_vision.infrastructure.platform import (
    Platform,
    cache_dir,
    config_dir,
    current_platform,
    data_dir,
    log_dir,
)

_PATCH = "trcc_vision.infrastructure.platform"


class TestCurrentPlatform:
    def test_linux(self) -> None:
        with patch(f"{_PATCH}.sys") as m:
            m.platform = "linux"
            assert current_platform() == Platform.LINUX

    def test_macos(self) -> None:
        with patch(f"{_PATCH}.sys") as m:
            m.platform = "darwin"
            assert current_platform() == Platform.MACOS

    def test_windows(self) -> None:
        with patch(f"{_PATCH}.sys") as m:
            m.platform = "win32"
            assert current_platform() == Platform.WINDOWS

    def test_freebsd(self) -> None:
        with patch(f"{_PATCH}.sys") as m:
            m.platform = "freebsd13"
            assert current_platform() == Platform.BSD

    def test_openbsd(self) -> None:
        with patch(f"{_PATCH}.sys") as m:
            m.platform = "openbsd7"
            assert current_platform() == Platform.BSD

    def test_unknown(self) -> None:
        with patch(f"{_PATCH}.sys") as m:
            m.platform = "haiku"
            assert current_platform() == Platform.UNKNOWN


class TestConfigDir:
    def test_linux_uses_dot_dir(self) -> None:
        with patch(f"{_PATCH}.current_platform", return_value=Platform.LINUX):
            result = config_dir()
            assert result.name == ".trcc-vision"
            assert result.parent == Path.home()

    def test_windows_uses_appdata(self) -> None:
        mock_plat = patch(f"{_PATCH}.current_platform", return_value=Platform.WINDOWS)
        mock_env = patch.dict("os.environ", {"APPDATA": "/tmp/appdata"})
        with mock_plat, mock_env:
            assert config_dir() == Path("/tmp/appdata/trcc-vision")

    def test_macos_uses_library(self) -> None:
        with patch(f"{_PATCH}.current_platform", return_value=Platform.MACOS):
            result = config_dir()
            assert result.name == "trcc-vision"
            assert "Library" in str(result)

    def test_bsd_uses_dot_dir(self) -> None:
        with patch(f"{_PATCH}.current_platform", return_value=Platform.BSD):
            result = config_dir()
            assert result.name == ".trcc-vision"


class TestDataDir:
    def test_linux_under_dot_dir(self) -> None:
        with patch(f"{_PATCH}.current_platform", return_value=Platform.LINUX):
            result = data_dir()
            assert ".trcc-vision" in str(result)
            assert result.name == "data"

    def test_bsd_under_dot_dir(self) -> None:
        with patch(f"{_PATCH}.current_platform", return_value=Platform.BSD):
            result = data_dir()
            assert ".trcc-vision" in str(result)


class TestLogDir:
    def test_linux_under_dot_dir(self) -> None:
        with patch(f"{_PATCH}.current_platform", return_value=Platform.LINUX):
            result = log_dir()
            assert ".trcc-vision" in str(result)
            assert result.name == "logs"

    def test_windows(self) -> None:
        mock_plat = patch(f"{_PATCH}.current_platform", return_value=Platform.WINDOWS)
        mock_env = patch.dict("os.environ", {"LOCALAPPDATA": "/tmp/local"})
        with mock_plat, mock_env:
            result = log_dir()
            assert "trcc-vision" in str(result)
            assert result.name == "logs"

    def test_macos(self) -> None:
        with patch(f"{_PATCH}.current_platform", return_value=Platform.MACOS):
            result = log_dir()
            assert "Library" in str(result)
            assert result.name == "trcc-vision"


class TestAllDirsContainAppName:
    """Every dir helper returns a path containing the app identifier."""

    def test_config(self) -> None:
        assert "trcc-vision" in str(config_dir())

    def test_data(self) -> None:
        assert "trcc-vision" in str(data_dir())

    def test_cache(self) -> None:
        assert "trcc-vision" in str(cache_dir())

    def test_log(self) -> None:
        assert "trcc-vision" in str(log_dir())
