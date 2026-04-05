"""Theme use cases — list, load, save, delete themes."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from trcc_vision.core.events import ThemeApplied

if TYPE_CHECKING:
    from trcc_vision.core.enums import ThemeType
    from trcc_vision.core.events import EventBus
    from trcc_vision.core.models import ThemeConfig, ThemeInfo
    from trcc_vision.services.theme import ThemeService

log = logging.getLogger(__name__)


class ListThemes:
    """List available themes, optionally filtered by type."""

    def __init__(self, theme_service: ThemeService) -> None:
        self._svc = theme_service

    def execute(self, theme_type: ThemeType | None = None) -> list[ThemeInfo]:
        log.debug("Listing themes: filter=%s", theme_type)
        themes = self._svc.list_themes(theme_type)
        log.info("Found %d theme(s)", len(themes))
        return themes


class LoadTheme:
    """Parse and apply a theme configuration."""

    def __init__(self, theme_service: ThemeService, event_bus: EventBus) -> None:
        self._svc = theme_service
        self._bus = event_bus

    def execute(self, theme: ThemeInfo) -> ThemeConfig:
        log.info("Loading theme: %s", theme.name)
        config = self._svc.load_config(theme)
        self._bus.publish(ThemeApplied(theme_name=theme.name))
        log.info("Theme loaded: %s (%d elements)", theme.name, len(config.elements))
        return config


class SaveTheme:
    """Persist a theme configuration."""

    def __init__(self, theme_service: ThemeService) -> None:
        self._svc = theme_service

    def execute(self, theme: ThemeInfo, config: ThemeConfig) -> bool:
        log.info("Saving theme: %s", theme.name)
        try:
            self._svc.save_config(theme, config)
            return True
        except Exception:
            log.exception("Failed to save theme: %s", theme.name)
            return False


class DeleteTheme:
    """Remove a theme."""

    def __init__(self, theme_service: ThemeService) -> None:
        self._svc = theme_service

    def execute(self, theme: ThemeInfo) -> bool:
        log.info("Deleting theme: %s", theme.name)
        try:
            self._svc.delete(theme)
            return True
        except Exception:
            log.exception("Failed to delete theme: %s", theme.name)
            return False
