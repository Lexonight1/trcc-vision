"""Element toolbar — buttons for adding, deleting, and reordering theme elements."""

from __future__ import annotations

import logging

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QWidget

from trcc_vision.core.enums import ElementType, FontType, SensorType, TimerFormat
from trcc_vision.core.models import DataItem, ThemeElement

log = logging.getLogger(__name__)

_BTN_STYLE = """
    QPushButton {
        background: rgba(40, 40, 60, 200);
        color: white;
        border: 1px solid #444466;
        border-radius: 4px;
        padding: 5px 10px;
        font-size: 12px;
    }
    QPushButton:hover { background: rgba(60, 60, 90, 220); }
    QPushButton:pressed { background: rgba(80, 80, 120, 240); }
    QPushButton:disabled { color: #555577; }
"""


def create_default_element(element_type: ElementType) -> ThemeElement:
    """Create a sensible starter ThemeElement for the given type."""
    if element_type == ElementType.DATA:
        return ThemeElement(
            element_type=ElementType.DATA,
            content="0",
            data_item=DataItem(data_num=SensorType.CPU_TEMP, name="CPU Temp"),
            data_unit="°C",
            x=120, y=200,
            font_family="NI7SEG", font_size=48.0,
            font_type=FontType.CUSTOM, font_file_name="NI7SEG.TTF",
            color="#FFFFFF", opacity=1.0, z_index=10,
        )
    if element_type == ElementType.TIMER:
        return ThemeElement(
            element_type=ElementType.TIMER,
            timer_type=TimerFormat.TIME,
            x=120, y=300,
            font_family="NI7SEG", font_size=36.0,
            font_type=FontType.CUSTOM, font_file_name="NI7SEG.TTF",
            color="#FFFFFF", opacity=1.0, z_index=10,
        )
    if element_type == ElementType.IMAGE:
        return ThemeElement(
            element_type=ElementType.IMAGE,
            x=0, y=0, width=480, height=480,
            z_index=0, color="#FFFFFF", opacity=1.0,
        )
    # Fallback
    return ThemeElement(element_type=element_type, x=100, y=100, font_size=24.0)


class ElementToolbar(QWidget):
    """Toolbar with buttons for element CRUD and z-ordering."""

    add_data = Signal()
    add_timer = Signal()
    add_image = Signal()
    delete_selected = Signal()
    duplicate_selected = Signal()
    z_up = Signal()
    z_down = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setStyleSheet(_BTN_STYLE)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        layout.addWidget(self._btn("+ Data", self.add_data))
        layout.addWidget(self._btn("+ Timer", self.add_timer))
        layout.addWidget(self._btn("+ Image", self.add_image))
        layout.addWidget(self._sep())
        layout.addWidget(self._btn("Duplicate", self.duplicate_selected))
        layout.addWidget(self._btn("Delete", self.delete_selected))
        layout.addWidget(self._sep())
        layout.addWidget(self._btn("\u25b2 Forward", self.z_up))
        layout.addWidget(self._btn("\u25bc Back", self.z_down))
        layout.addStretch()

    @staticmethod
    def _btn(text: str, signal: Signal) -> QPushButton:
        btn = QPushButton(text)
        btn.clicked.connect(signal.emit)
        return btn

    @staticmethod
    def _sep() -> QWidget:
        sep = QWidget()
        sep.setFixedWidth(8)
        return sep
