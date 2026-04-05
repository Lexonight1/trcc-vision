"""Theme editor canvas — QGraphicsScene with draggable theme elements.

EditorScene loads a ThemeConfig into interactive QGraphicsItems (images, text
overlays) that the user can drag to reposition. extract_config() reads the
current scene state back into a ThemeConfig for saving.
"""

from __future__ import annotations

import logging
from copy import deepcopy
from datetime import datetime
from typing import TYPE_CHECKING

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontMetricsF,
    QPainter,
    QPen,
    QPixmap,
    QUndoStack,
)
from PySide6.QtWidgets import QGraphicsObject, QGraphicsScene

from trcc_vision.adapters.gui.constants import (
    LCD_HEIGHT,
    LCD_WIDTH,
    THEME_ASSETS,
    resolve_theme_font,
)
from trcc_vision.core.enums import ElementType

if TYPE_CHECKING:
    from PySide6.QtWidgets import QGraphicsItem, QStyleOptionGraphicsItem

    from trcc_vision.core.models import ThemeConfig, ThemeElement

log = logging.getLogger(__name__)


# ── Canvas Items ───────────────────────────────────────────────────────────


class CanvasItem(QGraphicsObject):
    """Base class for all draggable theme elements on the editor canvas.

    Holds a reference to a ThemeElement and keeps its x/y in sync with the
    item's scene position. Subclasses implement paint() and boundingRect().
    """

    element_moved = Signal()
    element_changed = Signal()

    def __init__(self, element: ThemeElement, parent: QGraphicsItem | None = None) -> None:
        super().__init__(parent)
        self._element = element
        self._drag_start: QPointF | None = None

        self.setFlags(
            QGraphicsObject.GraphicsItemFlag.ItemIsMovable
            | QGraphicsObject.GraphicsItemFlag.ItemIsSelectable
            | QGraphicsObject.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.setPos(element.x, element.y)
        self.setZValue(element.z_index)
        self.setOpacity(element.opacity)

    @property
    def element(self) -> ThemeElement:
        return self._element

    def itemChange(self, change: QGraphicsObject.GraphicsItemChange, value: object) -> object:
        if change == QGraphicsObject.GraphicsItemChange.ItemPositionHasChanged:
            pos = self.pos()
            self._element.x = pos.x()
            self._element.y = pos.y()
            self.element_moved.emit()
        return super().itemChange(change, value)

    def mousePressEvent(self, event: object) -> None:
        """Record position at drag start for undo."""
        self._drag_start = QPointF(self.pos())
        super().mousePressEvent(event)  # type: ignore[arg-type]

    def mouseReleaseEvent(self, event: object) -> None:
        """Push MoveCommand if position changed during drag."""
        super().mouseReleaseEvent(event)  # type: ignore[arg-type]
        if self._drag_start is not None and self._drag_start != self.pos():
            scene = self.scene()
            if isinstance(scene, EditorScene) and scene.undo_stack is not None:
                from trcc_vision.adapters.gui.widgets.undo_commands import MoveCommand

                scene.undo_stack.push(
                    MoveCommand(self, self._drag_start, QPointF(self.pos()))
                )
        self._drag_start = None

    def _draw_selection(self, painter: QPainter) -> None:
        """Draw a dashed selection rect when this item is selected."""
        if self.isSelected():
            pen = QPen(QColor("#847148"), 1.5, Qt.PenStyle.DashLine)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(self.boundingRect())


class ImageItem(CanvasItem):
    """Renders an IMAGE element as a QPixmap on the canvas."""

    def __init__(self, element: ThemeElement, parent: QGraphicsItem | None = None) -> None:
        super().__init__(element, parent)
        self._pixmap = QPixmap()
        self._load_pixmap()

    def _load_pixmap(self) -> None:
        if not self._element.image_file_path:
            return
        path = THEME_ASSETS / "image" / self._element.image_file_path
        if path.exists():
            self._pixmap = QPixmap(str(path))
            # Full-screen images scale to LCD size
            if self._element.width >= LCD_WIDTH or self._element.width == 0:
                self._pixmap = self._pixmap.scaled(
                    LCD_WIDTH, LCD_HEIGHT,
                    Qt.AspectRatioMode.IgnoreAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
        else:
            log.debug("Image not found: %s", path)

    def boundingRect(self) -> QRectF:
        if self._pixmap.isNull():
            w = self._element.width or 100
            h = self._element.height or 100
            return QRectF(0, 0, w, h)
        return QRectF(0, 0, self._pixmap.width(), self._pixmap.height())

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionGraphicsItem,
        widget: object = None,
    ) -> None:
        if not self._pixmap.isNull():
            painter.drawPixmap(0, 0, self._pixmap)
        else:
            # Placeholder for missing images
            painter.setBrush(QColor(40, 40, 60))
            painter.setPen(QPen(QColor(80, 80, 100)))
            painter.drawRect(self.boundingRect())
            painter.setPen(QColor(120, 120, 140))
            painter.drawText(self.boundingRect(), Qt.AlignmentFlag.AlignCenter, "[Image]")
        self._draw_selection(painter)


class TextItem(CanvasItem):
    """Renders a DATA or TIMER element as styled text on the canvas."""

    def __init__(self, element: ThemeElement, parent: QGraphicsItem | None = None) -> None:
        super().__init__(element, parent)
        self._font = self._resolve_font()
        self._display_text = self._default_text()
        self._metrics = QFontMetricsF(self._font)

    def _resolve_font(self) -> QFont:
        """Resolve the element's font, loading custom TTF if needed."""
        return resolve_theme_font(
            self._element.font_family,
            self._element.font_file_name or "NI7SEG.TTF",
            self._element.font_size,
            self._element.font_weight,
            self._element.font_style,
        )

    def _default_text(self) -> str:
        """Return placeholder text when no live data is available."""
        if self._element.element_type == ElementType.DATA:
            return self._element.content or f"--{self._element.data_unit}"
        if self._element.element_type == ElementType.TIMER:
            now = datetime.now()
            if self._element.timer_type.value == 0:
                return now.strftime("%H:%M:%S")
            if self._element.timer_type.value == 1:
                return now.strftime("%Y/%m/%d")
            return now.strftime("%A")
        return self._element.content or "Text"

    def update_display_text(self, text: str) -> None:
        """Update the rendered text (called by live sensor/timer updates)."""
        if text != self._display_text:
            self.prepareGeometryChange()
            self._display_text = text
            self._metrics = QFontMetricsF(self._font)
            self.update()

    def refresh_font(self) -> None:
        """Rebuild font after property changes."""
        self.prepareGeometryChange()
        self._font = self._resolve_font()
        self._metrics = QFontMetricsF(self._font)
        self.update()
        self.element_changed.emit()

    def boundingRect(self) -> QRectF:
        rect = self._metrics.boundingRect(self._display_text)
        # Add small padding so selection rect isn't clipped
        return QRectF(0, 0, rect.width() + 4, rect.height() + 4)

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionGraphicsItem,
        widget: object = None,
    ) -> None:
        painter.setFont(self._font)
        color = QColor(self._element.color) if self._element.color else QColor(255, 255, 255)
        painter.setPen(color)
        painter.setOpacity(self._element.opacity)
        painter.drawText(0, self._metrics.ascent(), self._display_text)
        painter.setOpacity(1.0)
        self._draw_selection(painter)


# ── Editor Scene ───────────────────────────────────────────────────────────


class EditorScene(QGraphicsScene):
    """QGraphicsScene that manages theme elements for the editor.

    load_config() populates the scene from a ThemeConfig.
    extract_config() reads the current state back into a ThemeConfig.
    """

    item_selected = Signal(object)  # CanvasItem | None

    def __init__(self, parent: object = None) -> None:
        super().__init__(parent)
        self.setSceneRect(0, 0, LCD_WIDTH, LCD_HEIGHT)
        self._config: ThemeConfig | None = None
        self.undo_stack = QUndoStack(self)
        self.selectionChanged.connect(self._on_selection_changed)

    def load_config(self, config: ThemeConfig) -> None:
        """Clear the scene and populate it from a ThemeConfig."""
        self.clear()
        self._config = config

        for elem in sorted(config.elements, key=lambda e: e.z_index):
            self._create_item(elem)

        log.info("Loaded %d elements into editor scene", len(config.elements))

    def extract_config(self) -> ThemeConfig:
        """Build a ThemeConfig from the current scene state."""
        from trcc_vision.core.models import ThemeConfig as TC

        if not self._config:
            return TC()

        elements = [item.element for item in self._canvas_items()]
        return TC(
            name=self._config.name,
            theme_type=self._config.theme_type,
            rotation=self._config.rotation,
            elements=sorted(elements, key=lambda e: e.z_index),
            display_data=self._config.display_data,
            display_timer=self._config.display_timer,
            display_image=self._config.display_image,
            display_video=self._config.display_video,
            display_text_block=self._config.display_text_block,
        )

    def add_element(self, element: ThemeElement) -> CanvasItem:
        """Add a new element to the scene and return the created item."""
        from trcc_vision.adapters.gui.widgets.undo_commands import AddCommand

        item = self._create_item(element)
        if self._config:
            self._config.elements.append(element)
        item.setSelected(True)
        self.undo_stack.push(AddCommand(self, item, element))
        log.debug("Added %s element at (%.1f, %.1f) z=%d",
                  element.element_type.value, element.x, element.y, element.z_index)
        return item

    def delete_selected(self) -> list[ThemeElement]:
        """Remove all selected items. Returns the deleted elements."""
        from trcc_vision.adapters.gui.widgets.undo_commands import DeleteCommand

        deleted: list[ThemeElement] = []
        for item in self.selectedItems():
            if isinstance(item, CanvasItem):
                deleted.append(item.element)
                self.undo_stack.push(DeleteCommand(self, item, item.element))
        if deleted:
            log.debug("Deleted %d element(s)", len(deleted))
        return deleted

    def duplicate_selected(self) -> list[CanvasItem]:
        """Duplicate selected items with a +20px offset."""
        new_items: list[CanvasItem] = []
        for item in list(self.selectedItems()):
            if isinstance(item, CanvasItem):
                new_elem = deepcopy(item.element)
                new_elem.x += 20
                new_elem.y += 20
                new_item = self.add_element(new_elem)
                new_items.append(new_item)
        return new_items

    def change_z_order(self, delta: int) -> None:
        """Adjust z_index of selected items by delta."""
        from trcc_vision.adapters.gui.widgets.undo_commands import ZOrderCommand

        for item in self.selectedItems():
            if isinstance(item, CanvasItem):
                old_z = item.element.z_index
                new_z = old_z + delta
                self.undo_stack.push(ZOrderCommand(item, old_z, new_z))

    def _create_item(self, element: ThemeElement) -> CanvasItem:
        """Create the appropriate CanvasItem subclass for an element."""
        if element.element_type == ElementType.IMAGE:
            item: CanvasItem = ImageItem(element)
        elif element.element_type in (ElementType.DATA, ElementType.TIMER):
            item = TextItem(element)
        else:
            # VIDEO or unknown — render as placeholder image
            item = ImageItem(element)

        self.addItem(item)
        return item

    def _canvas_items(self) -> list[CanvasItem]:
        """Return all CanvasItem objects in the scene."""
        return [item for item in self.items() if isinstance(item, CanvasItem)]

    def _on_selection_changed(self) -> None:
        selected = [i for i in self.selectedItems() if isinstance(i, CanvasItem)]
        self.item_selected.emit(selected[0] if len(selected) == 1 else None)
