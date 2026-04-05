"""Theme browser page — LCD preview + theme thumbnails + sensor cards.

Layout from decompiled pageyj.xaml:
  4 columns: * | 1000 | 320 | *
  Left 390px: Apply button + 480x480 canvas scaled to 300x300
  Center ~600px: "Theme Preview" title + two WrapPanels (standard + custom)
  Right 320px: sensor cards in 2 columns (145x140 each) with bg images
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from trcc_vision.adapters.gui.constants import (
    COLOR_ACCENT,
    GUI_ASSETS,
    SENSOR_CARD_HEIGHT,
    SENSOR_CARD_WIDTH,
    THEME_ASSETS,
    THEME_PREVIEW_DISPLAY,
    THEME_PREVIEW_LEFT_WIDTH,
    THEME_SENSOR_PANEL_WIDTH,
)
from trcc_vision.adapters.gui.widgets.image_button import ImageButton
from trcc_vision.adapters.gui.widgets.lcd_preview import LCDPreview
from trcc_vision.adapters.gui.widgets.theme_card import ThemeCard
from trcc_vision.core.enums import SensorType
from trcc_vision.core.events import SensorUpdated
from trcc_vision.infrastructure.i18n import t
from trcc_vision.infrastructure.theme_xml_parser import ThemeXmlParser

if TYPE_CHECKING:
    from trcc_vision.core.context import AppContext
    from trcc_vision.core.models import ThemeConfig, ThemeInfo

log = logging.getLogger(__name__)

# Sensor cards: (SensorType, bg_image, label_key)
# Order and bg images match pageyj.xaml button definitions
_SENSOR_CARDS_LEFT: list[tuple[int, str, str]] = [
    (SensorType.CPU_TEMP, "card_cpu_usage.png", "sensor.cpu_temp"),
    (SensorType.CPU_LOAD, "card_cpu_temp.png", "sensor.cpu_load"),
    (SensorType.CPU_SPEED, "card_cpu_voltage.png", "sensor.cpu_speed"),
    (SensorType.CPU_POWER, "card_generic.png", "sensor.cpu_power"),
    (SensorType.CPU_VOLTAGE, "card_generic.png", "sensor.cpu_voltage"),
    (SensorType.RAM_USED, "card_generic.png", "sensor.ram_used"),
    (SensorType.RAM_AVAILABLE, "card_generic.png", "sensor.ram_available"),
    (SensorType.RAM_USAGE_RATE, "card_generic.png", "sensor.ram_usage"),
    (SensorType.HDD_TEMP, "card_generic.png", "sensor.hdd_temp"),
]

_SENSOR_CARDS_RIGHT: list[tuple[int, str, str]] = [
    (SensorType.GPU_TEMP, "card_cpu_usage.png", "sensor.gpu_temp"),
    (SensorType.GPU_LOAD, "card_cpu_temp.png", "sensor.gpu_load"),
    (SensorType.GPU_SPEED, "card_cpu_voltage.png", "sensor.gpu_speed"),
    (SensorType.GPU_POWER, "card_cpu_voltage.png", "sensor.gpu_power"),
    (SensorType.HDD_CAPACITY, "card_generic.png", "sensor.hdd_capacity"),
    (SensorType.HDD_USAGE, "card_generic.png", "sensor.hdd_usage"),
    (SensorType.LAN_UPLOAD, "card_generic.png", "sensor.upload"),
    (SensorType.LAN_DOWNLOAD, "card_generic.png", "sensor.download"),
]


class PageTheme(QWidget):
    """Theme browser — matches pageyj.xaml 3-panel layout."""

    edit_requested = Signal(object, object)  # (ThemeInfo, ThemeConfig)

    def __init__(self, ctx: AppContext) -> None:
        super().__init__()
        self._ctx = ctx
        self._parser = ThemeXmlParser()
        self._cards: list[ThemeCard] = []
        self._sensor_labels: dict[int, QLabel] = {}
        self._selected_theme: str | None = None
        self._selected_theme_info: ThemeInfo | None = None
        self._selected_config: ThemeConfig | None = None

        self.setStyleSheet("background: transparent;")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self._setup_preview_panel(layout)
        self._setup_theme_list(layout)
        self._setup_sensor_panel(layout)

        ctx.event_bus.subscribe(SensorUpdated, self._on_sensor_updated)
        log.info("PageTheme created (XAML-matched layout)")

    # ── Left Panel: LCD Preview + Apply ───────────────────────────────

    def _setup_preview_panel(self, parent: QHBoxLayout) -> None:
        left = QWidget()
        left.setFixedWidth(THEME_PREVIEW_LEFT_WIDTH)
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(10, 0, 0, 0)
        left_layout.setSpacing(10)

        # Apply button (XAML: 应用按键.png, 220x55)
        apply_btn = ImageButton(
            GUI_ASSETS / "btn_apply_gold.png", tooltip=t("gui.btn.apply"),
        )
        apply_btn.clicked.connect(self._on_apply)
        left_layout.addWidget(apply_btn, 0, Qt.AlignmentFlag.AlignCenter)

        # LCD preview: 480x480 rendered, displayed at 300x300 (XAML Viewbox)
        preview_container = QWidget()
        preview_container.setFixedSize(
            THEME_PREVIEW_DISPLAY + 4, THEME_PREVIEW_DISPLAY + 4,
        )
        preview_container.setStyleSheet(
            f"border: 1px solid {COLOR_ACCENT}; border-radius: 5px; background: black;"
        )

        self._preview = LCDPreview(preview_container)
        # Scale the 480x480 widget to fit 300x300 display
        # LCDPreview renders at 480x480 internally but we display at 300x300
        self._preview.setFixedSize(THEME_PREVIEW_DISPLAY, THEME_PREVIEW_DISPLAY)

        left_layout.addWidget(preview_container, 0, Qt.AlignmentFlag.AlignCenter)

        # Edit button
        edit_btn = ImageButton(
            GUI_ASSETS / "btn_apply.png", tooltip=t("gui.btn.edit"),
        )
        edit_btn.clicked.connect(self._on_edit)
        left_layout.addWidget(edit_btn, 0, Qt.AlignmentFlag.AlignCenter)

        left_layout.addStretch()
        parent.addWidget(left)

    # ── Center Panel: Theme Thumbnails ────────────────────────────────

    def _setup_theme_list(self, parent: QHBoxLayout) -> None:
        center = QWidget()
        center_layout = QVBoxLayout(center)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(5)

        title = QLabel(t("gui.theme.theme_preview"))
        title.setStyleSheet(
            "color: white; font-size: 15px; font-weight: bold; background: transparent;"
        )
        center_layout.addWidget(title)

        # Standard presets (XAML: wp_DefaultTheme WrapPanel)
        standard_scroll = self._make_theme_scroll()
        standard_container = QWidget()
        standard_container.setStyleSheet("background: transparent;")
        self._standard_grid = QGridLayout(standard_container)
        self._standard_grid.setSpacing(5)
        self._standard_grid.setContentsMargins(5, 5, 5, 5)

        self._load_default_themes()

        standard_scroll.setWidget(standard_container)
        center_layout.addWidget(standard_scroll, 1)

        # Custom themes (XAML: wp_CustomerTheme WrapPanel)
        custom_scroll = self._make_theme_scroll()
        custom_container = QWidget()
        custom_container.setStyleSheet("background: transparent;")
        self._custom_grid = QGridLayout(custom_container)
        self._custom_grid.setSpacing(5)
        self._custom_grid.setContentsMargins(5, 5, 5, 5)
        # TODO: load user themes here
        custom_scroll.setWidget(custom_container)
        center_layout.addWidget(custom_scroll, 1)

        parent.addWidget(center, 1)

    def _make_theme_scroll(self) -> QScrollArea:
        """Create a scroll area matching XAML: white border, CornerRadius=7."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(
            "QScrollArea { background: transparent; "
            "border: 1px solid white; border-radius: 7px; }"
            f"QScrollBar:vertical {{ background: {COLOR_ACCENT}22; width: 6px; }}"
            f"QScrollBar::handle:vertical {{ background: {COLOR_ACCENT}; border-radius: 3px; }}"
        )
        return scroll

    # ── Right Panel: Sensor Cards ─────────────────────────────────────

    def _setup_sensor_panel(self, parent: QHBoxLayout) -> None:
        right = QWidget()
        right.setFixedWidth(THEME_SENSOR_PANEL_WIDTH)

        # Background image (XAML: 硬件参数外框.png)
        bg = QPixmap(str(GUI_ASSETS / "bg_sensor_panel.png"))
        if not bg.isNull():
            bg_label = QLabel(right)
            scaled = bg.scaled(
                THEME_SENSOR_PANEL_WIDTH, 600,
                Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            bg_label.setPixmap(scaled)
            bg_label.setGeometry(0, 0, THEME_SENSOR_PANEL_WIDTH, 600)

        scroll = QScrollArea(right)
        scroll.setGeometry(5, 5, THEME_SENSOR_PANEL_WIDTH - 10, 590)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
            "QScrollBar:vertical { background: transparent; width: 0px; }"
        )

        card_container = QWidget()
        card_container.setStyleSheet("background: transparent;")
        grid = QHBoxLayout(card_container)
        grid.setContentsMargins(0, 5, 0, 5)
        grid.setSpacing(0)

        # Left column of sensor cards (XAML: Grid Column=0)
        left_col = QVBoxLayout()
        left_col.setSpacing(10)
        for sensor_type, bg_file, label_key in _SENSOR_CARDS_LEFT:
            left_col.addWidget(self._make_sensor_card(sensor_type, bg_file, label_key))
        left_col.addStretch()
        grid.addLayout(left_col)

        # Right column of sensor cards (XAML: Grid Column=1)
        right_col = QVBoxLayout()
        right_col.setSpacing(10)
        for sensor_type, bg_file, label_key in _SENSOR_CARDS_RIGHT:
            right_col.addWidget(self._make_sensor_card(sensor_type, bg_file, label_key))
        right_col.addStretch()
        grid.addLayout(right_col)

        scroll.setWidget(card_container)
        parent.addWidget(right)

    def _make_sensor_card(self, sensor_type: int, bg_file: str, label_key: str) -> QWidget:
        """Sensor card: 145x140 with background image, value + label overlay."""
        card = QWidget()
        card.setFixedSize(SENSOR_CARD_WIDTH, SENSOR_CARD_HEIGHT)

        # Background image (XAML: Background=ImageBrush)
        bg_path = GUI_ASSETS / bg_file
        bg_pixmap = QPixmap(str(bg_path))
        if not bg_pixmap.isNull():
            bg_label = QLabel(card)
            bg_label.setPixmap(bg_pixmap.scaled(
                SENSOR_CARD_WIDTH, SENSOR_CARD_HEIGHT,
                Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            ))
            bg_label.setGeometry(0, 0, SENSOR_CARD_WIDTH, SENSOR_CARD_HEIGHT)

        # Content overlay
        content = QWidget(card)
        content.setGeometry(0, 0, SENSOR_CARD_WIDTH, SENSOR_CARD_HEIGHT)
        content.setStyleSheet("background: transparent;")

        layout = QVBoxLayout(content)
        layout.setContentsMargins(22, 30, 22, 10)
        layout.setSpacing(0)

        # Value (XAML: FontSize=15, Bold, White)
        value_label = QLabel("—")
        value_label.setStyleSheet(
            "color: #ffffff; font-size: 15px; font-weight: bold; background: transparent;"
        )
        value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(value_label)

        # Sensor name (XAML: white, wrapping, centered)
        name_label = QLabel(t(label_key))
        name_label.setStyleSheet(
            "color: #ffffff; font-size: 10px; background: transparent;"
        )
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_label.setWordWrap(True)
        layout.addWidget(name_label)

        layout.addStretch()
        self._sensor_labels[sensor_type] = value_label
        return card

    # ── Theme Loading ─────────────────────────────────────────────────

    def _load_default_themes(self) -> None:
        cols = 8  # XAML WrapPanel width=540 / ~70px per card ≈ 8 columns

        for i in range(1, 11):
            xml_path = THEME_ASSETS / f"Theme{i}.xml"
            preview_path = THEME_ASSETS / f"Theme{i}.png"

            if not xml_path.exists():
                continue

            name = t(f"gui.theme.theme_{i}")
            card = ThemeCard(
                name=name,
                preview_path=preview_path if preview_path.exists() else None,
            )
            card.selected_signal.connect(self._on_theme_selected)
            self._cards.append(card)

            row = (i - 1) // cols
            col = (i - 1) % cols
            self._standard_grid.addWidget(card, row, col)

        log.info("Loaded %d default theme cards", len(self._cards))

    # ── Event Handlers ────────────────────────────────────────────────

    def _on_theme_selected(self, name: str) -> None:
        log.info("Theme selected: %s", name)
        self._selected_theme = name

        for card in self._cards:
            card.set_selected(card.theme_name == name)

        for i in range(1, 21):
            if t(f"gui.theme.theme_{i}") == name:
                xml_path = THEME_ASSETS / f"Theme{i}.xml"
                if not xml_path.exists():
                    break
                from trcc_vision.core.models import ThemeInfo as TI

                theme_info = TI(name=name, path=xml_path)
                if self._ctx.load_theme:
                    config = self._ctx.load_theme.execute(theme_info)
                else:
                    config = self._parser.parse(xml_path)
                self._selected_theme_info = theme_info
                self._selected_config = config
                self._preview.set_theme(config)
                log.debug("Theme config loaded: %d elements", len(config.elements))
                break

    def _on_edit(self) -> None:
        if not self._selected_theme_info or not self._selected_config:
            log.warning("No theme selected to edit")
            return
        log.info("Edit requested: %s", self._selected_theme_info.name)
        self.edit_requested.emit(self._selected_theme_info, self._selected_config)

    def _on_apply(self) -> None:
        if not self._selected_theme:
            log.warning("No theme selected to apply")
            return
        log.info("Applying theme: %s", self._selected_theme)
        # TODO: send theme to device via use case

    def _on_sensor_updated(self, event: SensorUpdated) -> None:
        self._preview.update_sensors(event.readings)
        for reading in event.readings:
            label = self._sensor_labels.get(reading.sensor_type)
            if label:
                label.setText(f"{reading.value:.1f}{reading.unit}")
