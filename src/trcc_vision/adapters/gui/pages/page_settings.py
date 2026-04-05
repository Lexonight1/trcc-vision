"""Settings page — language, brightness, temperature unit, about.

Matches C# PageSZ: toggle switches, radio buttons, slider, version info.
All settings saved via config persistence (when available) or in-memory.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from trcc_vision.adapters.gui.constants import GUI_ASSETS
from trcc_vision.infrastructure.i18n import setup_i18n, t

if TYPE_CHECKING:
    from trcc_vision.core.context import AppContext

log = logging.getLogger(__name__)


class PageSettings(QWidget):
    """Settings and about page."""

    def __init__(self, ctx: AppContext) -> None:
        super().__init__()
        self._ctx = ctx
        self.setStyleSheet("background: transparent;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 10, 20, 10)
        layout.setSpacing(15)

        # Settings background
        bg = QPixmap(str(GUI_ASSETS / "bg_settings.png"))
        if not bg.isNull():
            bg_label = QLabel(self)
            scaled = bg.scaled(
                1160, 460,
                Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            bg_label.setPixmap(scaled)
            bg_label.setGeometry(0, 0, 1160, 460)
            bg_label.lower()

        self._setup_startup(layout)
        self._setup_language(layout)
        self._setup_temperature(layout)
        self._setup_brightness(layout)
        self._setup_about(layout)

        layout.addStretch()

        # Load saved preferences from config
        self._load_saved_prefs()

        log.info("PageSettings created")

    def _setup_startup(self, parent: QVBoxLayout) -> None:
        """Start on boot / minimize to tray toggles."""
        group = self._make_group(t("gui.settings.startup_mode"))

        # Start on boot
        row1 = QHBoxLayout()
        self._start_on_boot = QCheckBox(t("gui.settings.start_on_boot"))
        self._start_on_boot.setStyleSheet(
            "QCheckBox { color: #ededed; background: transparent; font-size: 13px; }"
            "QCheckBox::indicator { width: 18px; height: 18px; }"
            "QCheckBox::indicator:checked { background: #847148; border: 1px solid #847148; }"
            "QCheckBox::indicator:unchecked { background: #222222; border: 1px solid #555; }"
        )
        self._start_on_boot.stateChanged.connect(self._on_startup_changed)
        row1.addWidget(self._start_on_boot)
        row1.addStretch()

        # Minimize to tray
        self._minimize_to_tray = QCheckBox(t("gui.settings.minimize_to_tray"))
        self._minimize_to_tray.setStyleSheet(self._start_on_boot.styleSheet())
        self._minimize_to_tray.stateChanged.connect(self._on_startup_changed)
        row1.addWidget(self._minimize_to_tray)
        row1.addStretch()

        group.layout().addLayout(row1)  # type: ignore[union-attr]
        parent.addWidget(group)

    def _setup_language(self, parent: QVBoxLayout) -> None:
        """Language selector."""
        group = self._make_group(t("settings.language"))

        row = QHBoxLayout()
        label = QLabel(t("settings.language"))
        label.setStyleSheet("color: #cccccc; font-size: 13px; background: transparent;")
        row.addWidget(label)

        self._lang_combo = QComboBox()
        self._lang_combo.setStyleSheet(
            "QComboBox { background: #2a2a3e; color: white; border: 1px solid #555; "
            "padding: 4px; min-width: 150px; }"
            "QComboBox::drop-down { border: none; }"
            "QComboBox QAbstractItemView { background: #2a2a3e; color: white; }"
        )

        from trcc_vision.infrastructure.i18n import _instance

        if _instance:
            for lang_code in _instance.available_languages():
                lang_key = f"gui.lang.{lang_code.replace('-', '_')}"
                display = t(lang_key) if t(lang_key) != lang_key else lang_code
                self._lang_combo.addItem(display, lang_code)

            # Select current
            current = _instance.current_language()
            for i in range(self._lang_combo.count()):
                if self._lang_combo.itemData(i) == current:
                    self._lang_combo.setCurrentIndex(i)
                    break

        self._lang_combo.currentIndexChanged.connect(self._on_language_changed)
        row.addWidget(self._lang_combo)
        row.addStretch()

        group.layout().addLayout(row)  # type: ignore[union-attr]
        parent.addWidget(group)

    def _setup_temperature(self, parent: QVBoxLayout) -> None:
        """Temperature unit selector."""
        group = self._make_group(t("gui.settings.temp_display"))

        row = QHBoxLayout()
        self._radio_celsius = QRadioButton(t("gui.settings.celsius"))
        self._radio_celsius.setStyleSheet("color: #cccccc; background: transparent;")
        self._radio_celsius.setChecked(True)
        row.addWidget(self._radio_celsius)

        self._radio_fahrenheit = QRadioButton(t("gui.settings.fahrenheit"))
        self._radio_fahrenheit.setStyleSheet("color: #cccccc; background: transparent;")
        row.addWidget(self._radio_fahrenheit)

        row.addStretch()
        group.layout().addLayout(row)  # type: ignore[union-attr]
        parent.addWidget(group)

    def _setup_brightness(self, parent: QVBoxLayout) -> None:
        """Brightness slider (0-100)."""
        group = self._make_group(t("gui.settings.brightness"))

        row = QHBoxLayout()
        self._brightness_slider = QSlider(Qt.Orientation.Horizontal)
        self._brightness_slider.setRange(0, 100)
        self._brightness_slider.setValue(100)
        self._brightness_slider.setStyleSheet(
            "QSlider::groove:horizontal { background: #333355; height: 6px; border-radius: 3px; }"
            "QSlider::handle:horizontal { background: #847148; width: 16px; "
            "margin: -5px 0; border-radius: 8px; }"
        )
        self._brightness_slider.setMinimumWidth(300)
        row.addWidget(self._brightness_slider)

        self._brightness_label = QLabel("100%")
        self._brightness_label.setStyleSheet(
            "color: white; font-size: 14px; background: transparent;"
        )
        self._brightness_label.setMinimumWidth(50)
        row.addWidget(self._brightness_label)

        self._brightness_slider.valueChanged.connect(self._on_brightness_changed)

        row.addStretch()
        group.layout().addLayout(row)  # type: ignore[union-attr]
        parent.addWidget(group)

    def _setup_about(self, parent: QVBoxLayout) -> None:
        """Version info + check update section."""
        group = self._make_group(t("settings.about"))
        glayout = group.layout()
        assert glayout is not None

        info = self._ctx.get_system_info.execute()

        # Software version row
        sw_row = QHBoxLayout()
        sw_label = QLabel(t("gui.settings.software_version"))
        sw_label.setStyleSheet("color: #ededed; font-size: 13px; background: transparent;")
        sw_row.addWidget(sw_label)
        sw_val = QLabel(info.app_version)
        sw_val.setStyleSheet("color: #847148; font-size: 13px; font-weight: bold; "
                             "background: transparent;")
        sw_row.addWidget(sw_val)
        sw_row.addStretch()
        glayout.addLayout(sw_row)

        # Terminal version row
        tv_row = QHBoxLayout()
        tv_label = QLabel(t("gui.settings.terminal_version"))
        tv_label.setStyleSheet("color: #ededed; font-size: 13px; background: transparent;")
        tv_row.addWidget(tv_label)
        tv_val = QLabel("—")  # populated when device connects
        tv_val.setStyleSheet("color: #847148; font-size: 13px; font-weight: bold; "
                             "background: transparent;")
        tv_row.addWidget(tv_val)
        tv_row.addStretch()

        update_btn = QPushButton(t("gui.settings.check_update"))
        update_btn.setStyleSheet(
            "QPushButton { background: #847148; color: white; border: none; "
            "border-radius: 4px; padding: 6px 16px; font-size: 12px; }"
            "QPushButton:hover { background: #A1864B; }"
        )
        update_btn.clicked.connect(lambda: log.info("Check update clicked (not implemented)"))
        tv_row.addWidget(update_btn)
        glayout.addLayout(tv_row)

        # Platform info
        platform_text = (
            f"Python {info.python_version.split()[0]}  |  "
            f"{info.platform_name}  |  {info.os_version}"
        )
        platform_label = QLabel(platform_text)
        platform_label.setStyleSheet("color: #777777; font-size: 11px; background: transparent;")
        platform_label.setWordWrap(True)
        glayout.addWidget(platform_label)

        parent.addWidget(group)

    def _make_group(self, title: str) -> QGroupBox:
        """Create a styled group box."""
        group = QGroupBox(title)
        group.setStyleSheet(
            "QGroupBox { color: white; font-size: 14px; font-weight: bold; "
            "border: 1px solid #444466; border-radius: 6px; padding-top: 20px; "
            "margin-top: 10px; background: rgba(30, 30, 50, 150); }"
            "QGroupBox::title { subcontrol-origin: margin; left: 15px; padding: 0 5px; }"
        )
        group.setLayout(QVBoxLayout())
        return group

    def _load_saved_prefs(self) -> None:
        """Load saved preferences from config on startup."""
        if not hasattr(self._ctx, "config"):
            return
        cfg = self._ctx.config

        # Brightness
        brightness = cfg.get("brightness", 100)
        if isinstance(brightness, int):
            self._brightness_slider.setValue(brightness)

        # Temperature unit
        temp_unit = cfg.get("temp_unit", "celsius")
        if temp_unit == "fahrenheit":
            self._radio_fahrenheit.setChecked(True)
        else:
            self._radio_celsius.setChecked(True)

        # Language (already handled by i18n setup from config)
        log.debug("Loaded saved preferences from config")

    def _on_startup_changed(self) -> None:
        """Save startup/minimize preferences."""
        if hasattr(self._ctx, "config"):
            self._ctx.config.set("start_on_boot", self._start_on_boot.isChecked())
            self._ctx.config.set("minimize_to_tray", self._minimize_to_tray.isChecked())
        log.debug("Startup prefs: boot=%s tray=%s",
                  self._start_on_boot.isChecked(), self._minimize_to_tray.isChecked())

    def _on_language_changed(self, index: int) -> None:
        """Handle language selection change, save, and refresh visible labels."""
        lang_code = self._lang_combo.itemData(index)
        if not lang_code:
            return

        log.info("Language changed to: %s", lang_code)
        setup_i18n(lang_code)

        if hasattr(self._ctx, "config"):
            self._ctx.config.set("language", lang_code)

        # Refresh labels on this page
        self._radio_celsius.setText(t("gui.settings.celsius"))
        self._radio_fahrenheit.setText(t("gui.settings.fahrenheit"))

    def _on_brightness_changed(self, value: int) -> None:
        """Handle brightness slider change and save."""
        self._brightness_label.setText(f"{value}%")

        if hasattr(self._ctx, "config"):
            self._ctx.config.set("brightness", value)

        if self._ctx.set_brightness:
            self._ctx.set_brightness.execute(value)
            log.info("Brightness set to %d%%", value)
