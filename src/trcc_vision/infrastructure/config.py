"""JSON config persistence — implements ConfigPort.

Stores user preferences at config_dir()/config.json.
Auto-creates directory and file on first access.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from trcc_vision.core.ports import ConfigPort
from trcc_vision.infrastructure.platform import config_dir

if TYPE_CHECKING:
    from pathlib import Path

log = logging.getLogger(__name__)

_DEFAULT_CONFIG = {
    "language": "en",
    "brightness": 100,
    "temp_unit": "celsius",
    "minimize_to_tray": True,
    "start_on_boot": False,
}


class JsonConfig(ConfigPort):
    """Reads and writes user preferences to a JSON file."""

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or (config_dir() / "config.json")
        self._data: dict = {}
        self._load_or_create()

    def load(self) -> dict:
        """Load config from disk."""
        if not self._path.exists():
            log.debug("Config file not found, using defaults: %s", self._path)
            return dict(_DEFAULT_CONFIG)
        try:
            raw = self._path.read_text(encoding="utf-8")
            data = json.loads(raw)
            log.debug("Config loaded: %d keys from %s", len(data), self._path)
            return data
        except (json.JSONDecodeError, OSError):
            log.exception("Failed to load config: %s", self._path)
            return dict(_DEFAULT_CONFIG)

    def save(self, data: dict) -> None:
        """Persist config to disk."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        log.debug("Config saved: %d keys to %s", len(data), self._path)

    def get(self, key: str, default: object = None) -> object:
        """Get a single config value."""
        value = self._data.get(key, default)
        log.debug("Config get: %s = %r", key, value)
        return value

    def set(self, key: str, value: object) -> None:
        """Set a single config value and persist immediately."""
        log.debug("Config set: %s = %r", key, value)
        self._data[key] = value
        self.save(self._data)

    def _load_or_create(self) -> None:
        """Load existing config or create with defaults."""
        existed = self._path.exists()
        self._data = self.load()
        # Merge defaults for any missing keys
        for k, v in _DEFAULT_CONFIG.items():
            if k not in self._data:
                self._data[k] = v
        if not existed:
            self.save(self._data)
            log.info("Config created with defaults at %s", self._path)
