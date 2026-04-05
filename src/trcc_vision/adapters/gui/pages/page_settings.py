"""Settings page — 2-column layout matching decompiled pagesz.xaml.

Left column (980px): startup toggles, temp/language, brightness — all inside
bg_settings_frame.png with bg_label_setting.png label backgrounds.
Right column (300px): software + terminal version with check-update buttons.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QRadioButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from trcc_vision.adapters.gui.constants import (
    COLOR_ACCENT,
    COLOR_CYAN,
    COLOR_TEXT,
    COLOR_TEXT_DIM,
    GUI_ASSETS,
    SETTINGS_LABEL_WIDTH,
    SETTINGS_LEFT_WIDTH,
    SETTINGS_RIGHT_WIDTH,
)
from trcc_vision.adapters.gui.widgets.image_button import ImageButton
from trcc_vision.infrastructure.i18n import setup_i18n, t

if TYPE_CHECKING:
    from trcc_vision.core.context import AppContext

log = logging.getLogger(__name__)


def _label_with_bg(text: str) -> QWidget:
    """Create a 190px label with bg_label_setting.png background (XAML: Label背景)."""
    container = QWidget()
    container.setFixedSize(SETTINGS_LABEL_WIDTH, 40)

    bg = QPixmap(str(GUI_ASSETS / "bg_label_setting.png"))
    if not bg.isNull():
        bg_label = QLabel(container)
        bg_label.setPixmap(bg.scaled(
            SETTINGS_LABEL_WIDTH, 40,
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        ))
        bg_label.setGeometry(0, 0, SETTINGS_LABEL_WIDTH, 40)

    text_label = QLabel(text, container)
    text_label.setGeometry(0, 0, SETTINGS_LABEL_WIDTH, 40)
    text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    text_label.setStyleSheet(
        f"color: {COLOR_TEXT}; font-size: 15px; background: transparent;"
    )
    text_label.setWordWrap(True)
    return container


class PageSettings(QWidget):
    """Settings and about page — 2-column layout from pagesz.xaml."""

    def __init__(self, ctx: AppContext) -> None:
        super().__init__()
        self._ctx = ctx
        self.setStyleSheet("background: transparent;")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(20)

        self._setup_left_column(layout)
        self._setup_right_column(layout)

        self._load_saved_prefs()
        log.info("PageSettings created (XAML-matched 2-column layout)")

    # ── Left Column (980px) ───────────────────────────────────────────

    def _setup_left_column(self, parent: QHBoxLayout) -> None:
        left = QWidget()
        left.setFixedWidth(SETTINGS_LEFT_WIDTH)
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)

        # Title + divider
        title = QLabel(t("gui.nav.settings_about"))
        title.setStyleSheet(
            "color: white; font-size: 20px; font-weight: bold; background: transparent;"
        )
        left_layout.addWidget(title)

        # Settings frame with background image (XAML: 设置边框.png)
        frame = QWidget()
        frame_bg = QPixmap(str(GUI_ASSETS / "bg_settings_frame.png"))
        if not frame_bg.isNull():
            bg_label = QLabel(frame)
            bg_label.setPixmap(frame_bg.scaled(
                SETTINGS_LEFT_WIDTH - 50, 420,
                Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            ))
            bg_label.setGeometry(0, 0, SETTINGS_LEFT_WIDTH - 50, 420)
            bg_label.lower()

        frame_layout = QVBoxLayout(frame)
        frame_layout.setContentsMargins(30, 30, 30, 30)
        frame_layout.setSpacing(0)

        # Row 1: Start Up + Minimize (XAML: height 60, margin 30)
        row1 = QHBoxLayout()
        row1.setSpacing(30)
        self._setup_startup_row(row1)
        frame_layout.addLayout(row1)
        frame_layout.addSpacing(30)

        # Row 2: Temperature + Language (XAML: height 60, margin 30)
        row2 = QHBoxLayout()
        row2.setSpacing(30)
        self._setup_temp_lang_row(row2)
        frame_layout.addLayout(row2)
        frame_layout.addSpacing(30)

        # Row 3: Brightness (XAML: height 60, margin 30)
        row3 = QHBoxLayout()
        self._setup_brightness_row(row3)
        frame_layout.addLayout(row3)
        frame_layout.addStretch()

        left_layout.addWidget(frame, 1)
        parent.addWidget(left)

    def _setup_startup_row(self, row: QHBoxLayout) -> None:
        """Start on boot + Minimize on startup — side by side."""
        # Start on boot
        row.addWidget(_label_with_bg(t("gui.settings.start_on_boot")))
        self._start_on_boot = QCheckBox(t("gui.btn.on"))
        self._start_on_boot.setStyleSheet(self._toggle_style())
        self._start_on_boot.stateChanged.connect(self._on_startup_changed)
        row.addWidget(self._start_on_boot)
        row.addStretch()

        # Minimize to tray
        row.addWidget(_label_with_bg(t("gui.settings.minimize_to_tray")))
        self._minimize_to_tray = QCheckBox(t("gui.btn.on"))
        self._minimize_to_tray.setStyleSheet(self._toggle_style())
        self._minimize_to_tray.stateChanged.connect(self._on_startup_changed)
        row.addWidget(self._minimize_to_tray)
        row.addStretch()

    def _setup_temp_lang_row(self, row: QHBoxLayout) -> None:
        """Temperature display + Language selector — side by side."""
        # Temperature
        row.addWidget(_label_with_bg(t("gui.settings.temp_display")))
        self._radio_celsius = QRadioButton(t("gui.settings.celsius"))
        self._radio_celsius.setStyleSheet(self._radio_style())
        self._radio_celsius.setChecked(True)
        row.addWidget(self._radio_celsius)
        self._radio_fahrenheit = QRadioButton(t("gui.settings.fahrenheit"))
        self._radio_fahrenheit.setStyleSheet(self._radio_style())
        row.addWidget(self._radio_fahrenheit)
        row.addStretch()

        # Language
        row.addWidget(_label_with_bg(t("settings.language")))
        self._lang_combo = QComboBox()
        self._lang_combo.setFixedWidth(130)
        self._lang_combo.setStyleSheet(
            f"QComboBox {{ background: {COLOR_ACCENT}; color: #222222; "
            "border: none; padding: 4px; font-size: 15px; }}"
            "QComboBox::drop-down { border: none; }"
            f"QComboBox QAbstractItemView {{ background: {COLOR_ACCENT}; color: #222222; }}"
        )

        from trcc_vision.infrastructure.i18n import _instance

        if _instance:
            for lang_code in _instance.available_languages():
                lang_key = f"gui.lang.{lang_code.replace('-', '_')}"
                display = t(lang_key) if t(lang_key) != lang_key else lang_code
                self._lang_combo.addItem(display, lang_code)

            current = _instance.current_language()
            for i in range(self._lang_combo.count()):
                if self._lang_combo.itemData(i) == current:
                    self._lang_combo.setCurrentIndex(i)
                    break

        self._lang_combo.currentIndexChanged.connect(self._on_language_changed)
        row.addWidget(self._lang_combo)
        row.addStretch()

    def _setup_brightness_row(self, row: QHBoxLayout) -> None:
        """Brightness slider — XAML: SliderStyle, width 400, value text font 20."""
        row.addWidget(_label_with_bg(t("gui.settings.brightness")))

        self._brightness_slider = QSlider(Qt.Orientation.Horizontal)
        self._brightness_slider.setRange(0, 100)
        self._brightness_slider.setValue(100)
        self._brightness_slider.setFixedWidth(400)
        self._brightness_slider.setStyleSheet(
            "QSlider::groove:horizontal { background: #b6b6b6; height: 4px; }"
            f"QSlider::sub-page:horizontal {{ background: {COLOR_ACCENT}; height: 4px; }}"
            "QSlider::handle:horizontal { background: white; width: 20px; height: 20px; "
            "margin: -8px 0; border-radius: 10px; }"
        )
        self._brightness_slider.valueChanged.connect(self._on_brightness_changed)
        row.addWidget(self._brightness_slider)

        self._brightness_label = QLabel("100")
        self._brightness_label.setStyleSheet(
            f"color: {COLOR_TEXT_DIM}; font-size: 20px; background: transparent;"
        )
        self._brightness_label.setFixedWidth(50)
        row.addWidget(self._brightness_label)
        row.addStretch()

    # ── Right Column (300px) ──────────────────────────────────────────

    def _setup_right_column(self, parent: QHBoxLayout) -> None:
        right = QWidget()
        right.setFixedWidth(SETTINGS_RIGHT_WIDTH)
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)

        # Header
        header = QLabel(t("gui.settings.software_version"))
        header.setStyleSheet(
            f"color: {COLOR_TEXT}; font-size: 16px; font-weight: bold; "
            "background: transparent;"
        )
        right_layout.addWidget(header)

        info = self._ctx.get_system_info.execute()

        # Software version section
        right_layout.addWidget(self._make_version_block(
            t("gui.settings.software_version"), info.app_version,
        ))

        # Terminal version section
        right_layout.addWidget(self._make_version_block(
            t("gui.settings.terminal_version"), "—",
            show_update_btn=True,
        ))

        right_layout.addStretch()
        parent.addWidget(right)

    def _make_version_block(
        self, title: str, version: str, *, show_update_btn: bool = False,
    ) -> QWidget:
        """Version display block: bg_label_setting title + version number + optional button."""
        block = QWidget()
        block_layout = QVBoxLayout(block)
        block_layout.setContentsMargins(0, 0, 0, 0)
        block_layout.setSpacing(5)

        # Title with label background (XAML: 255px wide Label背景)
        title_container = QWidget()
        title_container.setFixedSize(255, 50)
        bg = QPixmap(str(GUI_ASSETS / "bg_label_setting.png"))
        if not bg.isNull():
            bg_label = QLabel(title_container)
            bg_label.setPixmap(bg.scaled(
                255, 50,
                Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            ))
            bg_label.setGeometry(0, 0, 255, 50)
        title_label = QLabel(title, title_container)
        title_label.setGeometry(0, 0, 255, 50)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet(
            f"color: {COLOR_TEXT}; font-size: 16px; background: transparent;"
        )
        title_label.setWordWrap(True)
        block_layout.addWidget(title_container, 0, Qt.AlignmentFlag.AlignCenter)

        # Version number (XAML: FontSize=20, Bold)
        ver_label = QLabel(version)
        ver_label.setStyleSheet(
            f"color: {COLOR_TEXT}; font-size: 20px; font-weight: bold; "
            "background: transparent;"
        )
        ver_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        block_layout.addWidget(ver_label)

        # Check update button (XAML: 应用按键.png, 255x70)
        if show_update_btn:
            btn = ImageButton(
                GUI_ASSETS / "btn_apply_gold.png", tooltip=t("gui.settings.check_update"),
            )
            btn.clicked.connect(
                lambda: log.info("Check update clicked (not implemented)")
            )
            block_layout.addWidget(btn, 0, Qt.AlignmentFlag.AlignCenter)

        return block

    # ── Style helpers ─────────────────────────────────────────────────

    @staticmethod
    def _toggle_style() -> str:
        """Checkbox styled as toggle (XAML: Panuon Switch, cyan when checked)."""
        return (
            f"QCheckBox {{ color: {COLOR_TEXT}; font-size: 15px; background: transparent; }}"
            "QCheckBox::indicator { width: 32px; height: 16px; border-radius: 8px; }"
            "QCheckBox::indicator:unchecked { background: #DEDEDE; }"
            f"QCheckBox::indicator:checked {{ background: {COLOR_CYAN}; }}"
        )

    @staticmethod
    def _radio_style() -> str:
        """Radio button (XAML: PURadioButton, cyan when checked)."""
        return (
            f"QRadioButton {{ color: {COLOR_TEXT}; font-size: 15px; "
            "background: transparent; }}"
            "QRadioButton::indicator { width: 16px; height: 16px; }"
            "QRadioButton::indicator:unchecked { background: white; "
            "border: 2px solid white; border-radius: 8px; }"
            f"QRadioButton::indicator:checked {{ background: {COLOR_CYAN}; "
            f"border: 2px solid {COLOR_CYAN}; border-radius: 8px; }}"
        )

    # ── Event Handlers ────────────────────────────────────────────────

    def _load_saved_prefs(self) -> None:
        if not hasattr(self._ctx, "config"):
            return
        cfg = self._ctx.config
        brightness = cfg.get("brightness", 100)
        if isinstance(brightness, int):
            self._brightness_slider.setValue(brightness)
        temp_unit = cfg.get("temp_unit", "celsius")
        if temp_unit == "fahrenheit":
            self._radio_fahrenheit.setChecked(True)
        log.debug("Loaded saved preferences from config")

    def _on_startup_changed(self) -> None:
        if hasattr(self._ctx, "config"):
            self._ctx.config.set("start_on_boot", self._start_on_boot.isChecked())
            self._ctx.config.set("minimize_to_tray", self._minimize_to_tray.isChecked())
        log.debug("Startup prefs: boot=%s tray=%s",
                  self._start_on_boot.isChecked(), self._minimize_to_tray.isChecked())

    def _on_language_changed(self, index: int) -> None:
        lang_code = self._lang_combo.itemData(index)
        if not lang_code:
            return
        log.info("Language changed to: %s", lang_code)
        setup_i18n(lang_code)
        if hasattr(self._ctx, "config"):
            self._ctx.config.set("language", lang_code)

    def _on_brightness_changed(self, value: int) -> None:
        self._brightness_label.setText(str(value))
        if hasattr(self._ctx, "config"):
            self._ctx.config.set("brightness", value)
        if self._ctx.set_brightness:
            self._ctx.set_brightness.execute(value)
            log.info("Brightness set to %d%%", value)
