"""Hardware monitor page — sensor dashboard with live updating cards.

Matches C# PageYJ: sensor cards in a grid layout, updates every 2s
via SensorUpdated events. Fan status shown when device is connected.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, QTimer
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
    FAN_POLL_MS,
    GUI_ASSETS,
    HW_SIDEBAR_WIDTH,
    SENSOR_POLL_MS,
)
from trcc_vision.adapters.gui.widgets.sensor_card import SensorCard
from trcc_vision.core.events import SensorUpdated
from trcc_vision.infrastructure.i18n import t

if TYPE_CHECKING:
    from trcc_vision.core.context import AppContext
    from trcc_vision.core.models import SensorReading

log = logging.getLogger(__name__)


class PageHardware(QWidget):
    """Hardware monitoring page — sensor grid + fan status."""

    def __init__(self, ctx: AppContext) -> None:
        super().__init__()
        self._ctx = ctx
        self._sensor_cards: dict[int, SensorCard] = {}

        self.setStyleSheet("background: transparent;")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # Left sidebar
        self._setup_sidebar(layout)

        # Right panel — sensor cards
        self._setup_sensor_panel(layout)

        # Subscribe to sensor events
        ctx.event_bus.subscribe(SensorUpdated, self._on_sensor_updated)

        # Sensor polling timer
        self._sensor_timer = QTimer(self)
        self._sensor_timer.timeout.connect(self._poll_sensors)
        self._sensor_timer.start(SENSOR_POLL_MS)

        # Fan polling timer (if available)
        if ctx.get_fan_states:
            self._fan_timer = QTimer(self)
            self._fan_timer.timeout.connect(self._poll_fans)
            self._fan_timer.start(FAN_POLL_MS)

        # Initial read
        self._poll_sensors()

        log.info("PageHardware created")

    def _setup_sidebar(self, parent_layout: QHBoxLayout) -> None:
        """Left sidebar with hardware category labels."""
        sidebar = QWidget()
        sidebar.setFixedWidth(HW_SIDEBAR_WIDTH)

        # Sidebar background
        bg = QPixmap(str(GUI_ASSETS / "bg_hw_sidebar.png"))
        bg_label = QLabel(sidebar)
        if not bg.isNull():
            scaled = bg.scaled(
                HW_SIDEBAR_WIDTH, 650,
                Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            bg_label.setPixmap(scaled)
            bg_label.setGeometry(0, 0, HW_SIDEBAR_WIDTH, 650)

        # Category labels on top of background
        categories = QWidget(sidebar)
        categories.setGeometry(20, 20, HW_SIDEBAR_WIDTH - 40, 600)
        categories.setStyleSheet("background: transparent;")
        cat_layout = QVBoxLayout(categories)
        cat_layout.setSpacing(15)
        cat_layout.setContentsMargins(10, 10, 10, 10)

        # Hardware params title
        title = QLabel(t("gui.hw.params"))
        title.setStyleSheet(
            "color: white; font-size: 16px; font-weight: bold; background: transparent;"
        )
        cat_layout.addWidget(title)

        # System info section
        self._sys_info_label = QLabel("")
        self._sys_info_label.setStyleSheet(
            "color: #aaaaaa; font-size: 11px; background: transparent;"
        )
        self._sys_info_label.setWordWrap(True)
        cat_layout.addWidget(self._sys_info_label)

        # Fan status section
        self._fan_label = QLabel("")
        self._fan_label.setStyleSheet(
            "color: #847148; font-size: 12px; background: transparent; font-family: monospace;"
        )
        self._fan_label.setWordWrap(True)
        cat_layout.addWidget(self._fan_label)

        cat_layout.addStretch()

        # System info
        info = self._ctx.get_system_info.execute()
        self._sys_info_label.setText(
            f"{t('gui.hw.system_info')}\n"
            f"  {info.platform_name} / {info.machine}\n"
            f"  Python {info.python_version.split()[0]}"
        )

        parent_layout.addWidget(sidebar)

    def _setup_sensor_panel(self, parent_layout: QHBoxLayout) -> None:
        """Right panel with scrollable sensor card grid + background."""
        panel = QWidget()
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(0, 0, 0, 0)

        # Panel background image
        bg = QPixmap(str(GUI_ASSETS / "bg_hw_panel.png"))
        if not bg.isNull():
            bg_label = QLabel(panel)
            scaled = bg.scaled(
                687, 650,
                Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            bg_label.setPixmap(scaled)
            bg_label.setGeometry(0, 0, 687, 650)
            bg_label.lower()

        # Scroll area for sensor cards
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
            "QScrollBar:vertical { background: #222222; width: 8px; }"
            "QScrollBar::handle:vertical { background: #847148; border-radius: 4px; }"
        )

        self._card_container = QWidget()
        self._card_container.setStyleSheet("background: transparent;")
        self._card_grid = QGridLayout(self._card_container)
        self._card_grid.setSpacing(6)
        self._card_grid.setContentsMargins(10, 10, 10, 10)

        scroll.setWidget(self._card_container)
        panel_layout.addWidget(scroll)

        parent_layout.addWidget(panel, 1)

    def _poll_sensors(self) -> None:
        """Read sensors via use case (triggers SensorUpdated event)."""
        self._ctx.read_all_sensors.execute()

    def _poll_fans(self) -> None:
        """Read fan states if available."""
        if not self._ctx.get_fan_states:
            return
        states = self._ctx.get_fan_states.execute()
        lines = []
        for s in states:
            lines.append(f"  Fan {s.channel}: {s.rpm:>5d} RPM  {s.duty_percent:>3d}%")
        self._fan_label.setText(
            f"{t('gui.hw.cpu_fan_speed')}\n" + "\n".join(lines) if lines else ""
        )

    def _on_sensor_updated(self, event: SensorUpdated) -> None:
        """Update sensor cards with new readings."""
        for reading in event.readings:
            card = self._get_or_create_card(reading)
            card.update_reading(reading)

    def _get_or_create_card(self, reading: SensorReading) -> SensorCard:
        """Get existing card or create a new one for this sensor type."""
        key = reading.sensor_type
        if key not in self._sensor_cards:
            card = SensorCard(self._card_container)
            self._sensor_cards[key] = card

            # Position in grid (2 columns)
            idx = len(self._sensor_cards) - 1
            row = idx // 2
            col = idx % 2
            self._card_grid.addWidget(card, row, col)

            log.debug("Created sensor card: %s (row=%d, col=%d)", reading.label, row, col)

        return self._sensor_cards[key]
