"""Ports (interfaces) — abstract contracts that adapters must implement.

These define the hexagonal boundary. Services depend on ports, never on
concrete adapters. Each port is a thin ABC with no business logic.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from trcc_vision.core.models import DeviceInfo, FanState, SensorReading


class DevicePort(ABC):
    """Port for communicating with TR-VISION hardware."""

    @abstractmethod
    def connect(self, device: DeviceInfo) -> None:
        """Establish connection to device."""

    @abstractmethod
    def disconnect(self) -> None:
        """Close connection."""

    @abstractmethod
    def is_connected(self) -> bool:
        """Check if device is reachable."""

    @abstractmethod
    def send_frame(self, data: bytes, width: int, height: int) -> None:
        """Send a single LCD frame (RGB565 or raw bitmap)."""

    @abstractmethod
    def send_command(self, cmd: bytes) -> bytes:
        """Send a raw command and return the response."""


class SensorPort(ABC):
    """Port for reading hardware sensors (CPU, GPU, RAM, etc.)."""

    @abstractmethod
    def read_all(self) -> list[SensorReading]:
        """Read all available sensor values."""

    @abstractmethod
    def read_type(self, sensor_type: int) -> SensorReading | None:
        """Read a specific sensor by type."""


class FanPort(ABC):
    """Port for fan speed monitoring and control."""

    @abstractmethod
    def get_fan_states(self) -> list[FanState]:
        """Read current fan RPMs and duty cycles."""

    @abstractmethod
    def set_fan_duty(self, channel: int, duty_percent: int) -> None:
        """Set fan duty cycle (0-100)."""


class ConfigPort(ABC):
    """Port for persisting user configuration."""

    @abstractmethod
    def load(self) -> dict:
        """Load config from storage."""

    @abstractmethod
    def save(self, data: dict) -> None:
        """Persist config to storage."""

    @abstractmethod
    def get(self, key: str, default: object = None) -> object:
        """Get a single config value."""

    @abstractmethod
    def set(self, key: str, value: object) -> None:
        """Set a single config value and persist."""


class ThemeRepositoryPort(ABC):
    """Port for theme storage and retrieval."""

    @abstractmethod
    def list_themes(self) -> list[Path]:
        """List all available theme directories."""

    @abstractmethod
    def load_theme_config(self, theme_path: Path) -> bytes:
        """Read raw theme config file."""

    @abstractmethod
    def save_theme_config(self, theme_path: Path, data: bytes) -> None:
        """Write theme config file."""

    @abstractmethod
    def delete_theme(self, theme_path: Path) -> None:
        """Remove a theme directory."""
