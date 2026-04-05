"""Asset loader — font and image path resolution.

Searches bundled assets first, then system fonts as fallback.
Parses FontFileList.xml for the font registry.
"""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger(__name__)

# Package assets directory (relative to this file)
_ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
_FONTS_DIR = _ASSETS_DIR / "fonts"
_THEMES_DIR = _ASSETS_DIR / "themes"
_FONT_LIST_XML = _ASSETS_DIR / "FontFileList.xml"


@dataclass
class FontInfo:
    """Font entry from FontFileList.xml."""

    name: str
    file_name: str
    data_num: int


class AssetLoader:
    """Resolves paths to bundled fonts, theme images, and other assets."""

    def __init__(
        self,
        assets_dir: Path | None = None,
    ) -> None:
        self._assets_dir = assets_dir or _ASSETS_DIR
        self._fonts_dir = self._assets_dir / "fonts"
        self._themes_dir = self._assets_dir / "themes"
        self._font_registry: list[FontInfo] | None = None
        log.debug("AssetLoader initialized: %s", self._assets_dir)

    @property
    def assets_dir(self) -> Path:
        return self._assets_dir

    @property
    def themes_dir(self) -> Path:
        return self._themes_dir

    def get_font_path(self, font_file_name: str) -> Path | None:
        """Find a font file by name. Checks bundled fonts first."""
        if not font_file_name:
            return None

        # Check bundled fonts
        bundled = self._fonts_dir / font_file_name
        if bundled.exists():
            log.debug("Font found (bundled): %s", bundled)
            return bundled

        # Case-insensitive search in fonts dir
        if self._fonts_dir.exists():
            lower = font_file_name.lower()
            for f in self._fonts_dir.iterdir():
                if f.name.lower() == lower:
                    log.debug("Font found (case-insensitive): %s", f)
                    return f

        log.warning("Font not found: %s", font_file_name)
        return None

    def get_image_path(self, image_file: str, theme_dir: Path | None = None) -> Path | None:
        """Find a theme image file. Checks theme dir, then themes/image/."""
        if not image_file:
            return None

        # Check in specific theme directory
        if theme_dir:
            direct = theme_dir / image_file
            if direct.exists():
                return direct

        # Check in themes/image/ (shared images)
        shared = self._themes_dir / "image" / image_file
        if shared.exists():
            return shared

        log.warning("Image not found: %s", image_file)
        return None

    def list_fonts(self) -> list[FontInfo]:
        """Parse FontFileList.xml and return all registered fonts."""
        if self._font_registry is not None:
            return self._font_registry

        xml_path = self._assets_dir / "FontFileList.xml"
        if not xml_path.exists():
            log.warning("FontFileList.xml not found at %s", xml_path)
            self._font_registry = []
            return self._font_registry

        log.debug("Parsing font list: %s", xml_path)
        try:
            tree = ET.parse(xml_path)  # noqa: S314
            root = tree.getroot()
            items = root.find("ItemList")
            if items is None:
                self._font_registry = []
                return self._font_registry

            fonts: list[FontInfo] = []
            for item in items.findall("ComboxItem"):
                name_el = item.find("Name")
                file_el = item.find("FileName")
                num_el = item.find("DataNum")
                fonts.append(FontInfo(
                    name=name_el.text if name_el is not None and name_el.text else "",
                    file_name=file_el.text if file_el is not None and file_el.text else "",
                    data_num=int(num_el.text) if num_el is not None and num_el.text else 0,
                ))

            self._font_registry = fonts
            log.info("Loaded %d fonts from FontFileList.xml", len(fonts))
            return fonts

        except ET.ParseError:
            log.exception("Failed to parse FontFileList.xml")
            self._font_registry = []
            return self._font_registry

    def list_theme_dirs(self) -> list[Path]:
        """List all theme directories that have a Theme*.xml config."""
        if not self._themes_dir.exists():
            return []
        # Theme XMLs are at themes/Theme1.xml, themes/Theme2.xml, etc.
        return sorted(
            p for p in self._themes_dir.glob("Theme*.xml")
        )

    def get_theme_preview(self, theme_name: str) -> Path | None:
        """Get the preview PNG for a theme (e.g. Theme1.png)."""
        preview = self._themes_dir / f"{theme_name}.png"
        if preview.exists():
            return preview
        return None
