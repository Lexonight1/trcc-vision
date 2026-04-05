"""Theme service — load, save, parse theme configurations."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from trcc_vision.core.models import ThemeConfig, ThemeInfo

if TYPE_CHECKING:
    from pathlib import Path

    from trcc_vision.core.enums import ThemeType
    from trcc_vision.core.ports import ThemeRepositoryPort

log = logging.getLogger(__name__)


class ThemeService:
    """Manages theme CRUD and config parsing."""

    def __init__(self, repo: ThemeRepositoryPort) -> None:
        self._repo = repo

    def list_themes(self, theme_type: ThemeType | None = None) -> list[ThemeInfo]:
        """List available themes, optionally filtered by type."""
        log.debug("list_themes() called: filter=%s", theme_type)
        paths = self._repo.list_themes()
        themes = [self._build_theme_info(p) for p in paths]
        if theme_type:
            themes = [t for t in themes if t.theme_type == theme_type]
        log.info("Listed %d theme(s)", len(themes))
        return themes

    def load_config(self, theme: ThemeInfo) -> ThemeConfig:
        """Parse a theme's config file into a ThemeConfig model."""
        log.debug("load_config() called: theme=%s", theme.name)
        raw = self._repo.load_theme_config(theme.path)
        log.debug("Read %d bytes from theme config", len(raw))
        config = self._parse_config(raw)
        log.info("Loaded config for theme: %s (%d elements)", theme.name, len(config.elements))
        return config

    def save_config(self, theme: ThemeInfo, config: ThemeConfig) -> None:
        """Serialize and persist a ThemeConfig."""
        log.debug("save_config() called: theme=%s, elements=%d", theme.name, len(config.elements))
        raw = self._serialize_config(config)
        self._repo.save_theme_config(theme.path, raw)
        log.info("Saved config for theme: %s", theme.name)

    def delete(self, theme: ThemeInfo) -> None:
        """Delete a theme."""
        log.debug("delete() called: theme=%s path=%s", theme.name, theme.path)
        self._repo.delete_theme(theme.path)
        log.info("Deleted theme: %s", theme.name)

    def _build_theme_info(self, path: Path) -> ThemeInfo:
        """Build ThemeInfo from a theme directory path."""
        has_bg = (path / "00.png").exists()
        has_video = (path / "Theme.zt").exists()
        return ThemeInfo(
            name=path.name,
            path=path,
            has_background=has_bg,
            has_video=has_video,
        )

    def _parse_config(self, raw: bytes) -> ThemeConfig:
        """Parse theme XML bytes into ThemeConfig."""
        from trcc_vision.infrastructure.theme_xml_parser import ThemeXmlParser
        return ThemeXmlParser().parse_bytes(raw)

    def _serialize_config(self, config: ThemeConfig) -> bytes:
        """Serialize ThemeConfig to XML bytes."""
        from trcc_vision.infrastructure.theme_xml_parser import ThemeXmlParser
        return ThemeXmlParser().serialize_bytes(config)
