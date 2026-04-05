"""Theme editor page — interactive canvas for editing theme layouts.

Opens when the user clicks "Edit" on a selected theme in PageTheme.
Uses QGraphicsScene with draggable items for each theme element.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import (
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from trcc_vision.adapters.gui.constants import LCD_HEIGHT, LCD_WIDTH
from trcc_vision.adapters.gui.widgets.canvas_scene import EditorScene, TextItem
from trcc_vision.core.enums import ElementType
from trcc_vision.core.events import SensorUpdated

if TYPE_CHECKING:
    from trcc_vision.core.context import AppContext
    from trcc_vision.core.models import ThemeConfig, ThemeInfo

log = logging.getLogger(__name__)

# ── Styled button helper ──────────────────────────────────────────────────

_BTN_STYLE = """
    QPushButton {
        background: rgba(40, 40, 60, 200);
        color: white;
        border: 1px solid #555577;
        border-radius: 4px;
        padding: 6px 16px;
        font-size: 13px;
    }
    QPushButton:hover { background: rgba(60, 60, 90, 220); }
    QPushButton:pressed { background: rgba(80, 80, 120, 240); }
"""


class PageThemeEditor(QWidget):
    """Theme editor with interactive QGraphicsScene canvas."""

    back_requested = Signal()

    def __init__(
        self,
        ctx: AppContext,
        theme_info: ThemeInfo,
        config: ThemeConfig,
    ) -> None:
        super().__init__()
        self._ctx = ctx
        self._theme_info = theme_info
        self._config = config
        self._dirty = False

        self.setStyleSheet("background: transparent;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 0, 10, 10)
        layout.setSpacing(8)

        self._setup_toolbar(layout)
        self._setup_element_toolbar(layout)
        self._setup_canvas(layout)

        # Load theme into scene
        self._scene.load_config(config)

        # Undo/redo shortcuts
        from PySide6.QtGui import QKeySequence, QShortcut

        QShortcut(QKeySequence.StandardKey.Undo, self, self._scene.undo_stack.undo)
        QShortcut(QKeySequence.StandardKey.Redo, self, self._scene.undo_stack.redo)
        self._scene.undo_stack.cleanChanged.connect(self._on_clean_changed)

        # Subscribe to live sensor updates
        ctx.event_bus.subscribe(SensorUpdated, self._on_sensor_updated)

        log.info("Theme editor opened: %s", theme_info.name)

    # ── UI Setup ──────────────────────────────────────────────────────

    def _setup_toolbar(self, parent: QVBoxLayout) -> None:
        """Top toolbar with back, theme name, and save buttons."""
        row = QHBoxLayout()
        row.setSpacing(10)

        back_btn = QPushButton("\u2190 Back")
        back_btn.setStyleSheet(_BTN_STYLE)
        back_btn.clicked.connect(self._on_back)
        row.addWidget(back_btn)

        self._name_label = QLabel(self._theme_info.name)
        self._name_label.setStyleSheet(
            "color: white; font-size: 16px; font-weight: bold; background: transparent;"
        )
        row.addWidget(self._name_label)

        row.addStretch()

        save_btn = QPushButton("Save")
        save_btn.setStyleSheet(_BTN_STYLE)
        save_btn.clicked.connect(self._on_save)
        row.addWidget(save_btn)

        parent.addLayout(row)

    def _setup_element_toolbar(self, parent: QVBoxLayout) -> None:
        """Element add/delete/z-order toolbar."""
        from trcc_vision.adapters.gui.widgets.element_toolbar import (
            ElementToolbar,
            create_default_element,
        )

        self._elem_toolbar = ElementToolbar()
        self._elem_toolbar.add_data.connect(
            lambda: self._add_element(create_default_element(ElementType.DATA))
        )
        self._elem_toolbar.add_timer.connect(
            lambda: self._add_element(create_default_element(ElementType.TIMER))
        )
        self._elem_toolbar.add_image.connect(self._add_image_element)
        self._elem_toolbar.delete_selected.connect(self._delete_selected)
        self._elem_toolbar.duplicate_selected.connect(self._duplicate_selected)
        self._elem_toolbar.z_up.connect(lambda: self._scene.change_z_order(1))
        self._elem_toolbar.z_down.connect(lambda: self._scene.change_z_order(-1))

        parent.addWidget(self._elem_toolbar)

    def _setup_canvas(self, parent: QVBoxLayout) -> None:
        """Central canvas area with QGraphicsView."""
        canvas_row = QHBoxLayout()
        canvas_row.setSpacing(15)

        # Scene + View
        self._scene = EditorScene()
        self._view = QGraphicsView(self._scene)
        self._view.setFixedSize(LCD_WIDTH + 4, LCD_HEIGHT + 4)  # +4 for border
        self._view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._view.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self._view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._view.setStyleSheet(
            "QGraphicsView { background: #000000; border: 2px solid #333355; border-radius: 4px; }"
        )
        self._view.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

        canvas_row.addWidget(self._view)

        # Property panel
        from trcc_vision.adapters.gui.widgets.property_panel import PropertyPanel

        self._property_panel = PropertyPanel()
        self._property_panel.setMinimumWidth(300)
        canvas_row.addWidget(self._property_panel, 1)
        parent.addLayout(canvas_row, 1)

        # Track dirty state
        self._scene.item_selected.connect(self._on_item_selected)

    # ── Event Handlers ────────────────────────────────────────────────

    def _on_clean_changed(self, clean: bool) -> None:
        """Track dirty state from undo stack."""
        self._dirty = not clean

    def _on_item_selected(self, item: object) -> None:
        """Handle scene selection changes — populate property panel."""
        from trcc_vision.adapters.gui.widgets.canvas_scene import CanvasItem

        self._dirty = True
        if isinstance(item, CanvasItem):
            self._property_panel.set_item(item)
        else:
            self._property_panel.set_item(None)

    def _add_element(self, element: object) -> None:
        """Add a new element to the scene."""
        from trcc_vision.core.models import ThemeElement

        if isinstance(element, ThemeElement):
            self._scene.add_element(element)
            self._dirty = True
            log.debug("Element added: %s", element.element_type.value)

    def _add_image_element(self) -> None:
        """Open file dialog, then add an IMAGE element."""
        from pathlib import Path

        from PySide6.QtWidgets import QFileDialog

        from trcc_vision.adapters.gui.widgets.element_toolbar import create_default_element

        path, _ = QFileDialog.getOpenFileName(
            self, "Select Image", "", "Images (*.png *.jpg *.jpeg *.gif *.bmp)",
        )
        if not path:
            return

        # Copy to theme image directory
        import shutil

        from trcc_vision.adapters.gui.constants import THEME_ASSETS

        dest_dir = THEME_ASSETS / "image"
        dest_dir.mkdir(parents=True, exist_ok=True)
        src = Path(path)
        dest = dest_dir / src.name
        if not dest.exists():
            shutil.copy2(src, dest)

        elem = create_default_element(ElementType.IMAGE)
        elem.image_file_path = src.name
        self._scene.add_element(elem)
        self._dirty = True
        log.info("Imported image: %s → %s", src, dest)

    def _delete_selected(self) -> None:
        """Delete selected elements from the scene."""
        deleted = self._scene.delete_selected()
        if deleted:
            self._dirty = True
            self._property_panel.set_item(None)
            log.debug("Deleted %d element(s)", len(deleted))

    def _duplicate_selected(self) -> None:
        """Duplicate selected elements."""
        new_items = self._scene.duplicate_selected()
        if new_items:
            self._dirty = True

    def _on_save(self) -> None:
        """Save the current scene state via the SaveTheme use case."""
        config = self._scene.extract_config()

        if self._ctx.save_theme:
            success = self._ctx.save_theme.execute(self._theme_info, config)
            if success:
                self._scene.undo_stack.setClean()
                self._dirty = False
                log.info("Theme saved: %s", self._theme_info.name)
            else:
                QMessageBox.warning(self, "Error", "Failed to save theme.")
                log.error("Failed to save theme: %s", self._theme_info.name)
        else:
            log.warning("SaveTheme use case not available")

    def _on_back(self) -> None:
        """Navigate back to the theme browser."""
        if self._dirty:
            reply = QMessageBox.question(
                self,
                "Unsaved Changes",
                "You have unsaved changes. Discard them?",
                QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel,
            )
            if reply == QMessageBox.StandardButton.Cancel:
                return

        self._ctx.event_bus.unsubscribe(SensorUpdated, self._on_sensor_updated)
        self.back_requested.emit()

    def _on_sensor_updated(self, event: SensorUpdated) -> None:
        """Update live sensor text in DATA/TIMER items."""
        for item in self._scene.items():
            if not isinstance(item, TextItem):
                continue
            elem = item.element
            if elem.element_type.value == "Data":
                reading = next(
                    (r for r in event.readings if r.sensor_type == elem.data_item.data_num),
                    None,
                )
                if reading:
                    item.update_display_text(f"{reading.value:.0f}{elem.data_unit}")
