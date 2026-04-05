"""Theme browser page — LCD preview + theme thumbnails + sensor cards.

Matches C# PageYJ layout: LCD preview on left with Apply/Edit buttons,
theme thumbnail grid in center, sensor readout cards on right.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from trcc_vision.adapters.gui.constants import GUI_ASSETS, THEME_ASSETS
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

# Sensor card definitions: (SensorType, icon_file, label_key)
_SENSOR_CARDS: list[tuple[int, str, str]] = [
    (SensorType.CPU_TEMP, "icon_cpu_temp.png", "sensor.cpu_temp"),
    (SensorType.CPU_LOAD, "icon_cpu_usage.png", "sensor.cpu_load"),
    (SensorType.CPU_SPEED, "icon_cpu_freq.png", "sensor.cpu_speed"),
    (SensorType.CPU_POWER, "icon_cpu_power.png", "sensor.cpu_power"),
    (SensorType.CPU_VOLTAGE, "icon_cpu_voltage.png", "sensor.cpu_voltage"),
    (SensorType.GPU_TEMP, "icon_cpu_temp.png", "sensor.gpu_temp"),
    (SensorType.GPU_LOAD, "icon_cpu_usage.png", "sensor.gpu_load"),
    (SensorType.RAM_USAGE_RATE, "icon_cpu_usage.png", "sensor.ram_usage"),
]

_CARD_STYLE = """
    QWidget#sensorCard {
        background: rgba(40, 35, 25, 180);
        border: 1px solid #847148;
        border-radius: 8px;
    }
"""

_CARD_SIZE = 120


class PageTheme(QWidget):
    """Theme browser with 3-panel layout: preview | thumbnails | sensors."""

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

        # Left: LCD preview + buttons
        self._setup_preview(layout)

        # Center: theme thumbnail grid
        self._setup_theme_list(layout)

        # Right: sensor readout cards
        self._setup_sensor_panel(layout)

        # Subscribe to sensor updates
        ctx.event_bus.subscribe(SensorUpdated, self._on_sensor_updated)

        log.info("PageTheme created (3-panel layout)")

    # ── Left Panel: LCD Preview ───────────────────────────────────────

    def _setup_preview(self, parent: QHBoxLayout) -> None:
        """Left panel — LCD preview + Apply/Edit buttons."""
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(10, 0, 0, 0)

        title = QLabel(t("gui.theme.theme_preview"))
        title.setStyleSheet(
            "color: #ededed; font-size: 14px; font-weight: bold; background: transparent;"
        )
        left_layout.addWidget(title)

        # LCD preview with background frame
        preview_frame = QWidget()
        preview_frame.setFixedSize(500, 560)
        preview_frame.setStyleSheet("background: transparent;")

        # Frame background image
        from PySide6.QtGui import QPixmap

        frame_bg = QPixmap(str(GUI_ASSETS / "bg_theme_preview.png"))
        if not frame_bg.isNull():
            frame_label = QLabel(preview_frame)
            scaled = frame_bg.scaled(
                500, 560,
                Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            frame_label.setPixmap(scaled)
            frame_label.setGeometry(0, 0, 500, 560)
            frame_label.lower()

        # LCD preview centered in frame
        self._preview = LCDPreview(preview_frame)
        self._preview.move(10, 10)

        left_layout.addWidget(preview_frame, 0, Qt.AlignmentFlag.AlignCenter)

        # Action buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        apply_btn = ImageButton(
            GUI_ASSETS / "btn_apply.png", tooltip=t("gui.btn.apply"),
        )
        apply_btn.clicked.connect(self._on_apply)
        btn_row.addWidget(apply_btn)

        edit_btn = ImageButton(
            GUI_ASSETS / "btn_ok.png", tooltip=t("gui.btn.edit"),
        )
        edit_btn.clicked.connect(self._on_edit)
        btn_row.addWidget(edit_btn)

        btn_row.addStretch()
        left_layout.addLayout(btn_row)
        left_layout.addStretch()

        parent.addWidget(left)

    # ── Center Panel: Theme Thumbnails ────────────────────────────────

    def _setup_theme_list(self, parent: QHBoxLayout) -> None:
        """Center panel — scrollable theme thumbnail grid."""
        center = QWidget()
        center_layout = QVBoxLayout(center)
        center_layout.setContentsMargins(0, 0, 0, 0)

        title = QLabel(t("gui.theme.theme_list"))
        title.setStyleSheet(
            "color: #ededed; font-size: 14px; font-weight: bold; background: transparent;"
        )
        center_layout.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
            "QScrollBar:vertical { background: #222222; width: 8px; }"
            "QScrollBar::handle:vertical { background: #847148; border-radius: 4px; }"
        )

        card_container = QWidget()
        card_container.setStyleSheet("background: transparent;")
        self._card_grid = QGridLayout(card_container)
        self._card_grid.setSpacing(8)
        self._card_grid.setContentsMargins(5, 5, 5, 5)

        self._load_default_themes()

        scroll.setWidget(card_container)
        center_layout.addWidget(scroll, 1)

        parent.addWidget(center, 1)

    # ── Right Panel: Sensor Cards ─────────────────────────────────────

    def _setup_sensor_panel(self, parent: QHBoxLayout) -> None:
        """Right panel — sensor readout cards in a grid."""
        right = QWidget()
        right.setFixedWidth(280)
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 10, 0)
        right_layout.setSpacing(8)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
            "QScrollBar:vertical { background: #222222; width: 6px; }"
            "QScrollBar::handle:vertical { background: #847148; border-radius: 3px; }"
        )

        card_container = QWidget()
        card_container.setStyleSheet("background: transparent;")
        grid = QGridLayout(card_container)
        grid.setSpacing(6)
        grid.setContentsMargins(0, 0, 0, 0)

        cols = 2
        for idx, (sensor_type, icon_file, label_key) in enumerate(_SENSOR_CARDS):
            card = self._make_sensor_card(sensor_type, icon_file, label_key)
            grid.addWidget(card, idx // cols, idx % cols)

        scroll.setWidget(card_container)
        right_layout.addWidget(scroll, 1)

        parent.addWidget(right)

    def _make_sensor_card(self, sensor_type: int, icon_file: str, label_key: str) -> QWidget:
        """Create a single sensor readout card with icon."""
        from PySide6.QtGui import QPixmap

        card = QWidget()
        card.setObjectName("sensorCard")
        card.setFixedSize(_CARD_SIZE, _CARD_SIZE)
        card.setStyleSheet(_CARD_STYLE)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(2)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Icon
        icon_path = GUI_ASSETS / icon_file
        icon_pixmap = QPixmap(str(icon_path))
        if not icon_pixmap.isNull():
            icon_label = QLabel()
            icon_label.setPixmap(icon_pixmap.scaled(
                32, 32,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            ))
            icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            icon_label.setStyleSheet("background: transparent;")
            layout.addWidget(icon_label)

        # Value (large, prominent)
        value_label = QLabel("—")
        value_label.setStyleSheet(
            "color: #ededed; font-size: 16px; font-weight: bold; background: transparent;"
        )
        value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(value_label)

        # Sensor name
        name_label = QLabel(t(label_key))
        name_label.setStyleSheet(
            "color: #847148; font-size: 9px; background: transparent;"
        )
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_label.setWordWrap(True)
        layout.addWidget(name_label)

        self._sensor_labels[sensor_type] = value_label
        return card

    # ── Theme Loading ─────────────────────────────────────────────────

    def _load_default_themes(self) -> None:
        """Load the 10 bundled default themes as cards."""
        cols = 3

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
            self._card_grid.addWidget(card, row, col)

        log.info("Loaded %d default theme cards", len(self._cards))

    # ── Event Handlers ────────────────────────────────────────────────

    def _on_theme_selected(self, name: str) -> None:
        """Handle theme card click."""
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
        """Open the theme editor for the selected theme."""
        if not self._selected_theme_info or not self._selected_config:
            log.warning("No theme selected to edit")
            return
        log.info("Edit requested for: %s", self._selected_theme_info.name)
        self.edit_requested.emit(self._selected_theme_info, self._selected_config)

    def _on_apply(self) -> None:
        """Apply selected theme to device."""
        if not self._selected_theme:
            log.warning("No theme selected to apply")
            return
        log.info("Applying theme: %s", self._selected_theme)
        # TODO: send theme to device via use case

    def _on_sensor_updated(self, event: SensorUpdated) -> None:
        """Update LCD preview and sensor cards with live data."""
        self._preview.update_sensors(event.readings)

        for reading in event.readings:
            label = self._sensor_labels.get(reading.sensor_type)
            if label:
                label.setText(f"{reading.value:.1f}{reading.unit}")
