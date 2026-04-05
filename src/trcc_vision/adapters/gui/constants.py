"""GUI layout constants — derived from C# MainWindow.baml and asset dimensions.

All coordinates are in pixels, matching the original WPF layout.
"""

from __future__ import annotations

from pathlib import Path

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

# ── Theme page ──────────────────────────────────────────────────────────

THEME_LIST_WIDTH = 500
THEME_CARD_WIDTH = 140
THEME_CARD_HEIGHT = 160
THEME_PREVIEW_SIZE = 480

# ── Settings page ───────────────────────────────────────────────────────

SETTINGS_PANEL_WIDTH = 1165
SETTINGS_PANEL_HEIGHT = 465

# ── LCD preview ─────────────────────────────────────────────────────────

LCD_WIDTH = 480
LCD_HEIGHT = 480

# ── Sensor polling ──────────────────────────────────────────────────────

SENSOR_POLL_MS = 2000
FAN_POLL_MS = 3000
