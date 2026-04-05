"""Tests for JSON config persistence."""

from __future__ import annotations

from pathlib import Path

from trcc_vision.infrastructure.config import JsonConfig


class TestJsonConfig:
    def test_creates_file_on_init(self, tmp_path: Path) -> None:
        path = tmp_path / "config.json"
        JsonConfig(path=path)
        assert path.exists()

    def test_default_values(self, tmp_path: Path) -> None:
        cfg = JsonConfig(path=tmp_path / "config.json")
        assert cfg.get("language") == "en"
        assert cfg.get("brightness") == 100
        assert cfg.get("temp_unit") == "celsius"

    def test_set_and_get(self, tmp_path: Path) -> None:
        cfg = JsonConfig(path=tmp_path / "config.json")
        cfg.set("language", "zh")
        assert cfg.get("language") == "zh"

    def test_persists_across_instances(self, tmp_path: Path) -> None:
        path = tmp_path / "config.json"
        cfg1 = JsonConfig(path=path)
        cfg1.set("brightness", 50)

        cfg2 = JsonConfig(path=path)
        assert cfg2.get("brightness") == 50

    def test_get_missing_key_returns_default(self, tmp_path: Path) -> None:
        cfg = JsonConfig(path=tmp_path / "config.json")
        assert cfg.get("nonexistent", "fallback") == "fallback"

    def test_load_returns_dict(self, tmp_path: Path) -> None:
        cfg = JsonConfig(path=tmp_path / "config.json")
        data = cfg.load()
        assert isinstance(data, dict)
        assert "language" in data

    def test_save_and_load_roundtrip(self, tmp_path: Path) -> None:
        path = tmp_path / "config.json"
        cfg = JsonConfig(path=path)
        cfg.save({"custom_key": "custom_value", "number": 42})

        cfg2 = JsonConfig(path=path)
        data = cfg2.load()
        assert data["custom_key"] == "custom_value"
        assert data["number"] == 42

    def test_corrupt_file_falls_back_to_defaults(self, tmp_path: Path) -> None:
        path = tmp_path / "config.json"
        path.write_text("not valid json {{{", encoding="utf-8")
        cfg = JsonConfig(path=path)
        assert cfg.get("language") == "en"  # default

    def test_creates_parent_dirs(self, tmp_path: Path) -> None:
        path = tmp_path / "deep" / "nested" / "config.json"
        JsonConfig(path=path)
        assert path.exists()
