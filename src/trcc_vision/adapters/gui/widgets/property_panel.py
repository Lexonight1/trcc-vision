"""Property panel — live-editing form for the selected canvas item.

Shows/hides sections based on element type (DATA, TIMER, IMAGE).
Bidirectional sync: panel ↔ CanvasItem ↔ ThemeElement model.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from trcc_vision.core.enums import ElementType, SensorType, TimerFormat

if TYPE_CHECKING:
    from trcc_vision.adapters.gui.widgets.canvas_scene import CanvasItem

log = logging.getLogger(__name__)

_SECTION_STYLE = "color: #aaaacc; font-size: 12px; font-weight: bold; background: transparent;"
_LABEL_STYLE = "color: #ccccdd; font-size: 12px; background: transparent;"
_INPUT_STYLE = """
    QDoubleSpinBox, QSpinBox, QComboBox, QCheckBox {
        background: rgba(30, 30, 50, 200);
        color: white;
        border: 1px solid #444466;
        border-radius: 3px;
        padding: 3px;
    }
"""

# Map SensorType values to readable labels
_SENSOR_LABELS: list[tuple[int, str]] = [
    (SensorType.CPU_TEMP, "CPU Temperature"),
    (SensorType.CPU_LOAD, "CPU Load"),
    (SensorType.CPU_SPEED, "CPU Speed"),
    (SensorType.GPU_TEMP, "GPU Temperature"),
    (SensorType.RAM_USAGE_RATE, "RAM Usage"),
]


class PropertyPanel(QScrollArea):
    """Side panel for editing the selected canvas item's properties."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._item: CanvasItem | None = None
        self._updating = False  # guard against signal loops

        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
            "QScrollBar:vertical { background: #2a2a3e; width: 8px; }"
            "QScrollBar::handle:vertical { background: #555577; border-radius: 4px; }"
        )

        container = QWidget()
        container.setStyleSheet("background: transparent;" + _INPUT_STYLE)
        self._layout = QVBoxLayout(container)
        self._layout.setContentsMargins(5, 5, 5, 5)
        self._layout.setSpacing(4)

        self._build_position_section()
        self._build_font_section()
        self._build_color_section()
        self._build_sensor_section()
        self._build_timer_section()
        self._layout.addStretch()

        self.setWidget(container)
        self._set_all_enabled(False)

    # ── Position Section ──────────────────────────────────────────────

    def _build_position_section(self) -> None:
        self._layout.addWidget(self._section_label("Position"))
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._x_spin = QDoubleSpinBox()
        self._x_spin.setRange(-100, 600)
        self._x_spin.setDecimals(1)
        self._x_spin.valueChanged.connect(self._on_position_changed)
        form.addRow(self._field_label("X:"), self._x_spin)

        self._y_spin = QDoubleSpinBox()
        self._y_spin.setRange(-100, 600)
        self._y_spin.setDecimals(1)
        self._y_spin.valueChanged.connect(self._on_position_changed)
        form.addRow(self._field_label("Y:"), self._y_spin)

        self._z_spin = QSpinBox()
        self._z_spin.setRange(-10, 100)
        self._z_spin.valueChanged.connect(self._on_z_changed)
        form.addRow(self._field_label("Z-Index:"), self._z_spin)

        self._scale_x_spin = QDoubleSpinBox()
        self._scale_x_spin.setRange(0.1, 10.0)
        self._scale_x_spin.setSingleStep(0.1)
        self._scale_x_spin.setDecimals(2)
        self._scale_x_spin.valueChanged.connect(self._on_scale_changed)
        form.addRow(self._field_label("Scale X:"), self._scale_x_spin)

        self._scale_y_spin = QDoubleSpinBox()
        self._scale_y_spin.setRange(0.1, 10.0)
        self._scale_y_spin.setSingleStep(0.1)
        self._scale_y_spin.setDecimals(2)
        self._scale_y_spin.valueChanged.connect(self._on_scale_changed)
        form.addRow(self._field_label("Scale Y:"), self._scale_y_spin)

        self._layout.addLayout(form)

    # ── Font Section ──────────────────────────────────────────────────

    def _build_font_section(self) -> None:
        self._font_header = self._section_label("Font")
        self._layout.addWidget(self._font_header)
        self._font_form = QFormLayout()
        self._font_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._font_size_spin = QDoubleSpinBox()
        self._font_size_spin.setRange(8, 200)
        self._font_size_spin.setDecimals(1)
        self._font_size_spin.valueChanged.connect(self._on_font_changed)
        self._font_size_label = self._field_label("Size:")
        self._font_form.addRow(self._font_size_label, self._font_size_spin)

        self._bold_check = QCheckBox("Bold")
        self._bold_check.setStyleSheet("color: #ccccdd; background: transparent;")
        self._bold_check.stateChanged.connect(self._on_font_changed)
        self._font_form.addRow(self._field_label(""), self._bold_check)

        self._italic_check = QCheckBox("Italic")
        self._italic_check.setStyleSheet("color: #ccccdd; background: transparent;")
        self._italic_check.stateChanged.connect(self._on_font_changed)
        self._font_form.addRow(self._field_label(""), self._italic_check)

        self._layout.addLayout(self._font_form)

    # ── Color Section ─────────────────────────────────────────────────

    def _build_color_section(self) -> None:
        self._layout.addWidget(self._section_label("Color"))
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._color_btn = QPushButton("  ")
        self._color_btn.setFixedSize(60, 24)
        self._color_btn.clicked.connect(self._on_color_clicked)
        form.addRow(self._field_label("Color:"), self._color_btn)

        self._opacity_spin = QDoubleSpinBox()
        self._opacity_spin.setRange(0.0, 1.0)
        self._opacity_spin.setSingleStep(0.05)
        self._opacity_spin.setDecimals(2)
        self._opacity_spin.valueChanged.connect(self._on_opacity_changed)
        form.addRow(self._field_label("Opacity:"), self._opacity_spin)

        self._layout.addLayout(form)

    # ── Sensor Section ────────────────────────────────────────────────

    def _build_sensor_section(self) -> None:
        self._sensor_header = self._section_label("Sensor Binding")
        self._layout.addWidget(self._sensor_header)
        self._sensor_form = QFormLayout()
        self._sensor_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._sensor_combo = QComboBox()
        for val, label in _SENSOR_LABELS:
            self._sensor_combo.addItem(label, val)
        self._sensor_combo.currentIndexChanged.connect(self._on_sensor_changed)
        self._sensor_label = self._field_label("Sensor:")
        self._sensor_form.addRow(self._sensor_label, self._sensor_combo)

        self._layout.addLayout(self._sensor_form)

    # ── Timer Section ─────────────────────────────────────────────────

    def _build_timer_section(self) -> None:
        self._timer_header = self._section_label("Timer")
        self._layout.addWidget(self._timer_header)
        self._timer_form = QFormLayout()
        self._timer_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._timer_combo = QComboBox()
        self._timer_combo.addItem("Time (HH:MM:SS)", TimerFormat.TIME.value)
        self._timer_combo.addItem("Date (YYYY/MM/DD)", TimerFormat.DATE.value)
        self._timer_combo.addItem("Weekday", TimerFormat.WEEKDAY.value)
        self._timer_combo.currentIndexChanged.connect(self._on_timer_changed)
        self._timer_label = self._field_label("Format:")
        self._timer_form.addRow(self._timer_label, self._timer_combo)

        self._layout.addLayout(self._timer_form)

    # ── Public API ────────────────────────────────────────────────────

    def set_item(self, item: CanvasItem | None) -> None:
        """Populate the panel from the given item, or clear if None."""
        # Disconnect previous item signals
        if self._item is not None:
            import contextlib
            with contextlib.suppress(RuntimeError):
                self._item.element_moved.disconnect(self._on_item_moved)

        self._item = item

        if item is None:
            self._set_all_enabled(False)
            log.debug("Property panel cleared (no selection)")
            return

        self._set_all_enabled(True)
        item.element_moved.connect(self._on_item_moved)
        self._populate(item)
        log.debug("Property panel loaded: %s at (%.1f, %.1f)",
                  item.element.element_type.value, item.element.x, item.element.y)

    def _populate(self, item: CanvasItem) -> None:
        """Fill all editors from the item's element. Guards against signal loops."""
        self._updating = True
        elem = item.element

        # Position
        self._x_spin.setValue(elem.x)
        self._y_spin.setValue(elem.y)
        self._z_spin.setValue(elem.z_index)
        self._scale_x_spin.setValue(elem.scale_x)
        self._scale_y_spin.setValue(elem.scale_y)

        # Font (visible for text elements)
        is_text = elem.element_type in (ElementType.DATA, ElementType.TIMER)
        self._font_header.setVisible(is_text)
        self._font_size_spin.setVisible(is_text)
        self._font_size_label.setVisible(is_text)
        self._bold_check.setVisible(is_text)
        self._italic_check.setVisible(is_text)
        if is_text:
            self._font_size_spin.setValue(elem.font_size)
            self._bold_check.setChecked(elem.font_weight)
            self._italic_check.setChecked(elem.font_style)

        # Color
        self._color_btn.setStyleSheet(
            f"background-color: {elem.color}; border: 1px solid #666688;"
        )
        self._opacity_spin.setValue(elem.opacity)

        # Sensor (DATA only)
        is_data = elem.element_type == ElementType.DATA
        self._sensor_header.setVisible(is_data)
        self._sensor_combo.setVisible(is_data)
        self._sensor_label.setVisible(is_data)
        if is_data:
            idx = self._sensor_combo.findData(elem.data_item.data_num)
            if idx >= 0:
                self._sensor_combo.setCurrentIndex(idx)

        # Timer (TIMER only)
        is_timer = elem.element_type == ElementType.TIMER
        self._timer_header.setVisible(is_timer)
        self._timer_combo.setVisible(is_timer)
        self._timer_label.setVisible(is_timer)
        if is_timer:
            idx = self._timer_combo.findData(elem.timer_type.value)
            if idx >= 0:
                self._timer_combo.setCurrentIndex(idx)

        self._updating = False

    # ── Signal Handlers ───────────────────────────────────────────────

    def _on_position_changed(self) -> None:
        if self._updating or self._item is None:
            return
        self._item.setPos(self._x_spin.value(), self._y_spin.value())

    def _on_z_changed(self) -> None:
        if self._updating or self._item is None:
            return
        self._item.element.z_index = self._z_spin.value()
        self._item.setZValue(self._z_spin.value())
        self._item.element_changed.emit()

    def _on_scale_changed(self) -> None:
        if self._updating or self._item is None:
            return
        self._item.element.scale_x = self._scale_x_spin.value()
        self._item.element.scale_y = self._scale_y_spin.value()
        self._item.setTransformOriginPoint(
            self._item.boundingRect().center(),
        )
        self._item.setScale(self._scale_x_spin.value())
        self._item.element_changed.emit()

    def _on_font_changed(self) -> None:
        if self._updating or self._item is None:
            return
        from trcc_vision.adapters.gui.widgets.canvas_scene import TextItem

        elem = self._item.element
        elem.font_size = self._font_size_spin.value()
        elem.font_weight = self._bold_check.isChecked()
        elem.font_style = self._italic_check.isChecked()
        log.debug("Font changed: size=%.1f bold=%s italic=%s",
                  elem.font_size, elem.font_weight, elem.font_style)
        if isinstance(self._item, TextItem):
            self._item.refresh_font()

    def _on_color_clicked(self) -> None:
        if self._item is None:
            return
        current = QColor(self._item.element.color)
        color = QColorDialog.getColor(current, self, "Element Color")
        if color.isValid():
            log.debug("Color changed: %s → %s", self._item.element.color, color.name())
            self._item.element.color = color.name()
            self._color_btn.setStyleSheet(
                f"background-color: {color.name()}; border: 1px solid #666688;"
            )
            self._item.update()
            self._item.element_changed.emit()

    def _on_opacity_changed(self) -> None:
        if self._updating or self._item is None:
            return
        self._item.element.opacity = self._opacity_spin.value()
        self._item.setOpacity(self._opacity_spin.value())
        self._item.element_changed.emit()

    def _on_sensor_changed(self) -> None:
        if self._updating or self._item is None:
            return
        val = self._sensor_combo.currentData()
        if val is not None:
            self._item.element.data_item.data_num = val
            self._item.element_changed.emit()

    def _on_timer_changed(self) -> None:
        if self._updating or self._item is None:
            return
        from trcc_vision.adapters.gui.widgets.canvas_scene import TextItem

        val = self._timer_combo.currentData()
        if val is not None:
            self._item.element.timer_type = TimerFormat(val)
            if isinstance(self._item, TextItem):
                self._item.update_display_text(self._item._default_text())
            self._item.element_changed.emit()

    def _on_item_moved(self) -> None:
        """Sync panel X/Y when the item is dragged on the canvas."""
        if self._item is None:
            return
        self._updating = True
        self._x_spin.setValue(self._item.element.x)
        self._y_spin.setValue(self._item.element.y)
        self._updating = False

    # ── Helpers ───────────────────────────────────────────────────────

    def _set_all_enabled(self, enabled: bool) -> None:
        for child in self.widget().findChildren(QWidget):
            child.setEnabled(enabled)

    @staticmethod
    def _section_label(text: str) -> QLabel:
        label = QLabel(text)
        label.setStyleSheet(_SECTION_STYLE)
        return label

    @staticmethod
    def _field_label(text: str) -> QLabel:
        label = QLabel(text)
        label.setStyleSheet(_LABEL_STYLE)
        return label
