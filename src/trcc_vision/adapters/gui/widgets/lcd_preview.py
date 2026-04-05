"""LCD preview widget — renders a 480x480 theme preview using pure PySide6.

Composites background image + overlay text elements (sensor values,
time, date) positioned per theme coordinates. No Pillow dependency.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPixmap
from PySide6.QtWidgets import QLabel, QWidget

from trcc_vision.adapters.gui.constants import FONT_ASSETS, LCD_HEIGHT, LCD_WIDTH, THEME_ASSETS
from trcc_vision.core.enums import ElementType

if TYPE_CHECKING:
    from trcc_vision.core.models import SensorReading, ThemeConfig, ThemeElement

log = logging.getLogger(__name__)


class LCDPreview(QWidget):
    """480x480 LCD preview panel — renders themes with QPainter."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(LCD_WIDTH, LCD_HEIGHT)

        self._display = QLabel(self)
        self._display.setFixedSize(LCD_WIDTH, LCD_HEIGHT)
        self._display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._display.setStyleSheet(
            "background: #000000; border: 2px solid #333355; border-radius: 4px;"
        )

        self._config: ThemeConfig | None = None
        self._readings: dict[int, SensorReading] = {}

        log.debug("LCDPreview created: %dx%d", LCD_WIDTH, LCD_HEIGHT)

    def set_theme(self, config: ThemeConfig) -> None:
        """Set the active theme and re-render."""
        self._config = config
        self.render_preview()

    def update_sensors(self, readings: list[SensorReading]) -> None:
        """Update sensor values and re-render."""
        for r in readings:
            self._readings[r.sensor_type] = r
        if self._config:
            self.render_preview()

    def render_preview(self) -> None:
        """Render the theme preview using QPainter."""
        if not self._config:
            return

        try:
            canvas = QPixmap(LCD_WIDTH, LCD_HEIGHT)
            canvas.fill(QColor(0, 0, 0))

            painter = QPainter(canvas)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

            for elem in sorted(self._config.elements, key=lambda e: e.z_index):
                if elem.element_type == ElementType.IMAGE:
                    self._render_image(painter, elem)
                elif elem.element_type == ElementType.DATA:
                    self._render_data(painter, elem)
                elif elem.element_type == ElementType.TIMER:
                    self._render_timer(painter, elem)

            painter.end()
            self._display.setPixmap(canvas)

        except Exception:
            log.exception("Failed to render theme preview")

    def _render_image(self, painter: QPainter, elem: ThemeElement) -> None:
        """Render an IMAGE element (background)."""
        if not elem.image_file_path:
            return

        image_path = THEME_ASSETS / "image" / elem.image_file_path
        if not image_path.exists():
            log.debug("Theme image not found: %s", image_path)
            return

        pixmap = QPixmap(str(image_path))
        if pixmap.isNull():
            return

        x, y = int(elem.x), int(elem.y)
        if elem.width >= LCD_WIDTH or elem.width == 0:
            pixmap = pixmap.scaled(
                LCD_WIDTH, LCD_HEIGHT,
                Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        painter.drawPixmap(x, y, pixmap)

    def _render_data(self, painter: QPainter, elem: ThemeElement) -> None:
        """Render a DATA element (sensor value)."""
        reading = self._readings.get(elem.data_item.data_num)
        text = (
            f"{reading.value:.0f}{elem.data_unit}"
            if reading
            else elem.content or "---"
        )
        self._draw_text(painter, text, elem)

    def _render_timer(self, painter: QPainter, elem: ThemeElement) -> None:
        """Render a TIMER element (time/date)."""
        now = datetime.now()
        if elem.timer_type.value == 0:
            text = now.strftime("%H:%M:%S")
        elif elem.timer_type.value == 1:
            text = now.strftime("%Y/%m/%d")
        else:
            text = now.strftime("%A")
        self._draw_text(painter, text, elem)

    def _draw_text(self, painter: QPainter, text: str, elem: ThemeElement) -> None:
        """Draw text at the element's position with its font/color settings."""
        # Font
        font_path = FONT_ASSETS / (elem.font_file_name or "NI7SEG.TTF")
        if font_path.exists():
            from PySide6.QtGui import QFontDatabase
            font_id = QFontDatabase.addApplicationFont(str(font_path))
            families = QFontDatabase.applicationFontFamilies(font_id)
            family = families[0] if families else elem.font_family
        else:
            family = elem.font_family

        # WPF FontSize is in DIPs (1/96"), Qt uses points (1/72"): pts = DIPs * 0.75
        pt_size = int(elem.font_size * 0.75)
        font = QFont(family, pt_size)
        font.setBold(elem.font_weight)
        font.setItalic(elem.font_style)
        painter.setFont(font)

        # Color
        color = QColor(elem.color) if elem.color else QColor(255, 255, 255)
        painter.setPen(color)

        # Draw — QPainter.drawText y is baseline, add font ascent
        painter.setOpacity(elem.opacity)
        metrics = painter.fontMetrics()
        painter.drawText(int(elem.x), int(elem.y) + metrics.ascent(), text)
        painter.setOpacity(1.0)
