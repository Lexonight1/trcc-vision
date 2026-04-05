"""GUI layout constants — derived from C# MainWindow.baml and asset dimensions.

All coordinates are in pixels, matching the original WPF layout.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PySide6.QtGui import QFont

# ── Asset directories ───────────────────────────────────────────────────

_ASSETS_ROOT = Path(__file__).resolve().parent.parent.parent / "assets"
GUI_ASSETS = _ASSETS_ROOT / "gui"
THEME_ASSETS = _ASSETS_ROOT / "themes"
FONT_ASSETS = _ASSETS_ROOT / "fonts"

# ── Window ──────────────────────────────────────────────────────────────

WINDOW_WIDTH = 1400
WINDOW_HEIGHT = 800

# ── Title bar ───────────────────────────────────────────────────────────

TITLEBAR_HEIGHT = 72
TITLEBAR_DRAG_AREA = (0, 0, WINDOW_WIDTH, TITLEBAR_HEIGHT)

BTN_CLOSE_X = 1340
BTN_CLOSE_Y = 15
BTN_MIN_X = 1290
BTN_MIN_Y = 15

DEVICE_STATUS_X = 200
DEVICE_STATUS_Y = 25

# ── Navigation tabs ────────────────────────────────────────────────────

NAV_Y = 82
NAV_X_START = 30
NAV_TAB_WIDTH = 226
NAV_TAB_HEIGHT = 39
NAV_TAB_SPACING = 10

NAV_TABS = [
    {"key": "hardware", "icon": "icon_hardware.png", "label": "gui.nav.hardware_monitor"},
    {"key": "theme", "icon": "icon_media.png", "label": "gui.nav.display_settings"},
    {"key": "settings", "icon": "icon_settings.png", "label": "gui.nav.settings_about"},
]

# ── Content area ────────────────────────────────────────────────────────

CONTENT_X = 20
CONTENT_Y = 130
CONTENT_WIDTH = 1360
CONTENT_HEIGHT = 650

# ── Hardware page ───────────────────────────────────────────────────────

HW_SIDEBAR_X = 0
HW_SIDEBAR_WIDTH = 343
HW_PANEL_X = 353
HW_PANEL_WIDTH = 687
HW_CARD_WIDTH = 320
HW_CARD_HEIGHT = 49

# ── Color palette (from decompiled XAML) ───────────────────────────────

COLOR_ACCENT = "#847148"
COLOR_CYAN = "#02d0e8"
COLOR_TEXT = "#ededed"
COLOR_TEXT_DIM = "#dddddd"
COLOR_INPUT_BG = "#222222"
COLOR_HOVER_BG = "#363636"
COLOR_DISABLED = "#717171"

# ── Theme page (from pageyj.xaml) ──────────────────────────────────────

THEME_PREVIEW_LEFT_WIDTH = 390
THEME_PREVIEW_DISPLAY = 300   # 480x480 canvas scaled to 300x300 via Viewbox
THEME_SENSOR_PANEL_WIDTH = 320
THEME_CARD_WIDTH = 60         # XAML: Border Width=60
THEME_CARD_HEIGHT = 60        # XAML: Border Height=60
THEME_CARD_IMAGE = 30         # XAML: Image Width=30 Height=30

# Sensor cards (from pageyj.xaml: Button Width=145 Height=140)
SENSOR_CARD_WIDTH = 145
SENSOR_CARD_HEIGHT = 140

# ── Settings page (from pagesz.xaml) ───────────────────────────────────

SETTINGS_LEFT_WIDTH = 980     # XAML: ColumnDefinition Width=980
SETTINGS_RIGHT_WIDTH = 300    # XAML: ColumnDefinition Width=300
SETTINGS_LABEL_WIDTH = 190    # XAML: DockPanel Width=190 (Label背景)

# ── LCD preview ─────────────────────────────────────────────────────────

LCD_WIDTH = 480
LCD_HEIGHT = 480

# ── Theme editor ────────────────────────────────────────────────────

EDITOR_CANVAS_SIZE = 480
EDITOR_SELECTION_COLOR = "#847148"
EDITOR_PROPERTY_PANEL_WIDTH = 350

# ── Font resolution ─────────────────────────────────────────────────────


def resolve_theme_font(
    font_family: str,
    font_file_name: str,
    font_size_dips: float,
    bold: bool = False,
    italic: bool = False,
) -> QFont:
    """Build a QFont from WPF theme element font properties.

    Loads custom TTF from FONT_ASSETS if available, converts WPF DIPs
    (1/96") to Qt points (1/72"): pts = round(dips * 0.75).
    """
    from PySide6.QtGui import QFont, QFontDatabase

    family = font_family
    font_path = FONT_ASSETS / font_file_name
    if font_path.exists():
        font_id = QFontDatabase.addApplicationFont(str(font_path))
        families = QFontDatabase.applicationFontFamilies(font_id)
        if families:
            family = families[0]

    pt_size = round(font_size_dips * 0.75)
    font = QFont(family, pt_size)
    font.setBold(bold)
    font.setItalic(italic)
    return font


# ── Sensor polling ──────────────────────────────────────────────────────

SENSOR_POLL_MS = 2000
FAN_POLL_MS = 3000
