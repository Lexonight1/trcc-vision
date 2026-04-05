"""Sensor card widget — displays a single SensorReading with icon + value.

Matches the C# PageYJ sensor button layout: icon + label + value + unit,
with bg_hw_row.png background.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget

from trcc_vision.adapters.gui.constants import GUI_ASSETS, HW_CARD_HEIGHT, HW_CARD_WIDTH

if TYPE_CHECKING:
    from trcc_vision.core.models import SensorReading

log = logging.getLogger(__name__)

# Map sensor type to icon filename
_SENSOR_ICONS = {
    0: "icon_cpu_temp.png",     # CPU_TEMP
    1: "icon_cpu_temp.png",     # CPU_CORE_TEMP
    2: "icon_cpu_temp.png",     # CPU_PACKAGE_TEMP
    3: "icon_cpu_voltage.png",  # CPU_VOLTAGE
    4: "icon_cpu_power.png",    # CPU_POWER
    5: "icon_cpu_usage.png",    # CPU_LOAD
    7: "icon_cpu_freq.png",     # CPU_SPEED
    13: "icon_cpu_temp.png",    # GPU_TEMP (reuse cpu icon for now)
    17: "icon_cpu_fan.png",     # CPU_FAN_SPEED
}


class SensorCard(QWidget):
    """Displays one sensor reading: icon | label | value unit."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(HW_CARD_WIDTH, HW_CARD_HEIGHT)

        # Background
        bg = QPixmap(str(GUI_ASSETS / "bg_hw_row.png"))
        self._bg_label = QLabel(self)
        if not bg.isNull():
            scaled = bg.scaled(
                HW_CARD_WIDTH, HW_CARD_HEIGHT,
                Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self._bg_label.setPixmap(scaled)
        self._bg_label.setGeometry(0, 0, HW_CARD_WIDTH, HW_CARD_HEIGHT)

        # Content layout on top of background
        container = QWidget(self)
        container.setGeometry(0, 0, HW_CARD_WIDTH, HW_CARD_HEIGHT)
        container.setStyleSheet("background: transparent;")
        layout = QHBoxLayout(container)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)

        # Icon
        self._icon = QLabel()
        self._icon.setFixedSize(28, 28)
        self._icon.setStyleSheet("background: transparent;")
        layout.addWidget(self._icon)

        # Label
        self._label = QLabel("")
        self._label.setStyleSheet("color: #cccccc; font-size: 12px; background: transparent;")
        self._label.setMinimumWidth(120)
        layout.addWidget(self._label, 1)

        # Value + unit
        self._value = QLabel("")
        self._value.setStyleSheet(
            "color: #00ff88; font-size: 14px; font-weight: bold; background: transparent;"
        )
        self._value.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self._value)

    def update_reading(self, reading: SensorReading) -> None:
        """Update the card with a new sensor reading."""
        # Icon
        icon_name = _SENSOR_ICONS.get(reading.sensor_type, "icon_cpu_temp.png")
        icon_path = GUI_ASSETS / icon_name
        pixmap = QPixmap(str(icon_path))
        if not pixmap.isNull():
            self._icon.setPixmap(pixmap.scaled(
                28, 28,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            ))

        self._label.setText(reading.label)
        self._value.setText(f"{reading.value:.1f} {reading.unit}")
