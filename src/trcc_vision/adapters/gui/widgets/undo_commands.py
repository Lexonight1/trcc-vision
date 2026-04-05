"""QUndoCommand subclasses for the theme editor.

Each command encapsulates a reversible operation on the canvas.
MoveCommand supports merging so a full drag becomes one undo entry.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtGui import QUndoCommand

if TYPE_CHECKING:
    from PySide6.QtCore import QPointF

    from trcc_vision.adapters.gui.widgets.canvas_scene import CanvasItem, EditorScene
    from trcc_vision.core.models import ThemeElement

_MOVE_CMD_ID = 1001


class MoveCommand(QUndoCommand):
    """Undo/redo for item repositioning. Mergeable for smooth drag."""

    def __init__(
        self, item: CanvasItem, old_pos: QPointF, new_pos: QPointF,
    ) -> None:
        super().__init__(f"Move to ({new_pos.x():.0f}, {new_pos.y():.0f})")
        self._item = item
        self._old_pos = old_pos
        self._new_pos = new_pos

    def id(self) -> int:
        return _MOVE_CMD_ID

    def mergeWith(self, other: QUndoCommand) -> bool:
        """Merge consecutive moves of the same item into one command."""
        if not isinstance(other, MoveCommand):
            return False
        if other._item is not self._item:
            return False
        self._new_pos = other._new_pos
        return True

    def undo(self) -> None:
        self._item.setPos(self._old_pos)
        self._item.element.x = self._old_pos.x()
        self._item.element.y = self._old_pos.y()

    def redo(self) -> None:
        self._item.setPos(self._new_pos)
        self._item.element.x = self._new_pos.x()
        self._item.element.y = self._new_pos.y()


class PropertyChangeCommand(QUndoCommand):
    """Undo/redo for a single property edit on an element."""

    def __init__(
        self, item: CanvasItem, attr: str, old_value: object, new_value: object,
    ) -> None:
        super().__init__(f"Change {attr}")
        self._item = item
        self._attr = attr
        self._old = old_value
        self._new = new_value

    def undo(self) -> None:
        setattr(self._item.element, self._attr, self._old)
        self._item.update()

    def redo(self) -> None:
        setattr(self._item.element, self._attr, self._new)
        self._item.update()


class AddCommand(QUndoCommand):
    """Undo/redo for adding an element to the scene."""

    def __init__(self, scene: EditorScene, item: CanvasItem, element: ThemeElement) -> None:
        super().__init__(f"Add {element.element_type.value}")
        self._scene = scene
        self._item = item
        self._element = element

    def undo(self) -> None:
        self._scene.removeItem(self._item)
        if self._scene._config and self._element in self._scene._config.elements:
            self._scene._config.elements.remove(self._element)

    def redo(self) -> None:
        self._scene.addItem(self._item)
        if self._scene._config and self._element not in self._scene._config.elements:
            self._scene._config.elements.append(self._element)


class DeleteCommand(QUndoCommand):
    """Undo/redo for removing an element from the scene."""

    def __init__(self, scene: EditorScene, item: CanvasItem, element: ThemeElement) -> None:
        super().__init__(f"Delete {element.element_type.value}")
        self._scene = scene
        self._item = item
        self._element = element

    def undo(self) -> None:
        self._scene.addItem(self._item)
        if self._scene._config and self._element not in self._scene._config.elements:
            self._scene._config.elements.append(self._element)

    def redo(self) -> None:
        self._scene.removeItem(self._item)
        if self._scene._config and self._element in self._scene._config.elements:
            self._scene._config.elements.remove(self._element)


class ZOrderCommand(QUndoCommand):
    """Undo/redo for z-index changes."""

    def __init__(self, item: CanvasItem, old_z: int, new_z: int) -> None:
        super().__init__(f"Z-order {old_z} → {new_z}")
        self._item = item
        self._old_z = old_z
        self._new_z = new_z

    def undo(self) -> None:
        self._item.element.z_index = self._old_z
        self._item.setZValue(self._old_z)

    def redo(self) -> None:
        self._item.element.z_index = self._new_z
        self._item.setZValue(self._new_z)
