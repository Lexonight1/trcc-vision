"""File-based theme repository — implements ThemeRepositoryPort.

Scans two locations:
1. Bundled themes: assets/themes/ (read-only defaults, shipped with app)
2. User themes: data_dir()/themes/ (user-created, writable)
"""

from __future__ import annotations

import logging
import shutil
from typing import TYPE_CHECKING

from trcc_vision.core.ports import ThemeRepositoryPort

if TYPE_CHECKING:
    from pathlib import Path

log = logging.getLogger(__name__)


class FileThemeRepository(ThemeRepositoryPort):
    """Finds and manages themes on the filesystem."""

    def __init__(self, bundled_dir: Path, user_dir: Path) -> None:
        self._bundled = bundled_dir
        self._user = user_dir
        log.info(
            "ThemeRepository: bundled=%s, user=%s",
            self._bundled, self._user,
        )

    def list_themes(self) -> list[Path]:
        """List all theme XML paths from bundled + user directories."""
        themes: list[Path] = []

        # Bundled (read-only)
        if self._bundled.exists():
            themes.extend(sorted(self._bundled.glob("Theme*.xml")))

        # User themes
        if self._user.exists():
            themes.extend(sorted(self._user.glob("*.xml")))

        n_bundled = sum(1 for t in themes if self._is_bundled(t))
        log.debug("Listed %d theme(s): %d bundled, %d user",
                  len(themes), n_bundled, len(themes) - n_bundled)
        return themes

    def _is_bundled(self, path: Path) -> bool:
        """Check if a path is inside the bundled directory."""
        return self._bundled in path.parents or path.parent == self._bundled

    def load_theme_config(self, theme_path: Path) -> bytes:
        """Read raw theme XML bytes."""
        log.debug("Loading theme config: %s", theme_path)
        return theme_path.read_bytes()

    def save_theme_config(self, theme_path: Path, data: bytes) -> None:
        """Write theme config — only to user directory."""
        # Ensure writes go to user dir, not bundled
        if self._is_bundled(theme_path):
            # Redirect to user dir with same filename
            theme_path = self._user / theme_path.name
            log.debug("Redirected save to user dir: %s", theme_path)

        self._user.mkdir(parents=True, exist_ok=True)
        theme_path.write_bytes(data)
        log.info("Saved theme config: %s (%d bytes)", theme_path.name, len(data))

    def delete_theme(self, theme_path: Path) -> None:
        """Delete a theme — only from user directory."""
        if self._is_bundled(theme_path):
            log.warning("Cannot delete bundled theme: %s", theme_path)
            return

        if theme_path.exists():
            # If it's an XML, also try to delete associated PNG preview
            if theme_path.is_file():
                theme_path.unlink()
                preview = theme_path.with_suffix(".png")
                if preview.exists():
                    preview.unlink()
                log.info("Deleted theme: %s", theme_path.name)
            elif theme_path.is_dir():
                shutil.rmtree(theme_path)
                log.info("Deleted theme directory: %s", theme_path.name)
        else:
            log.warning("Theme not found for deletion: %s", theme_path)
