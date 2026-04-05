"""Tests for undo/redo commands in the theme editor."""

from __future__ import annotations

import pytest

from trcc_vision.core.enums import ElementType
from trcc_vision.core.models import DataItem, ThemeConfig, ThemeElement


@pytest.fixture()
def _qapp():
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture()
def scene(_qapp):  # noqa: PT004
    from trcc_vision.adapters.gui.widgets.canvas_scene import EditorScene

    s = EditorScene()
    s.load_config(ThemeConfig(
        name="Test",
        elements=[
            ThemeElement(
                element_type=ElementType.DATA,
                content="42", x=100, y=200, z_index=5, font_size=24.0,
                data_item=DataItem(data_num=0, name="CPU"),
            ),
        ],
    ))
    return s


def _data_item(scene):
    from trcc_vision.adapters.gui.widgets.canvas_scene import CanvasItem

    return next(i for i in scene.items() if isinstance(i, CanvasItem))


class TestMoveCommand:
    @pytest.mark.usefixtures("_qapp")
    def test_move_undo_redo(self, scene) -> None:
        from PySide6.QtCore import QPointF

        from trcc_vision.adapters.gui.widgets.undo_commands import MoveCommand

        item = _data_item(scene)
        old_pos = QPointF(100, 200)
        new_pos = QPointF(300, 400)

        cmd = MoveCommand(item, old_pos, new_pos)
        cmd.redo()
        assert abs(item.pos().x() - 300) < 0.1
        assert abs(item.element.x - 300) < 0.1

        cmd.undo()
        assert abs(item.pos().x() - 100) < 0.1
        assert abs(item.element.x - 100) < 0.1

    @pytest.mark.usefixtures("_qapp")
    def test_move_merge(self, scene) -> None:
        from PySide6.QtCore import QPointF

        from trcc_vision.adapters.gui.widgets.undo_commands import MoveCommand

        item = _data_item(scene)
        cmd1 = MoveCommand(item, QPointF(100, 200), QPointF(150, 250))
        cmd2 = MoveCommand(item, QPointF(150, 250), QPointF(300, 400))

        assert cmd1.mergeWith(cmd2) is True
        # After merge, undo goes back to original
        cmd1.redo()
        assert abs(item.pos().x() - 300) < 0.1

        cmd1.undo()
        assert abs(item.pos().x() - 100) < 0.1


class TestAddDeleteCommand:
    @pytest.mark.usefixtures("_qapp")
    def test_add_undo(self, scene) -> None:
        from trcc_vision.adapters.gui.widgets.canvas_scene import CanvasItem

        new_elem = ThemeElement(
            element_type=ElementType.TIMER, x=50, y=50, font_size=24.0,
        )
        scene.add_element(new_elem)
        items = [i for i in scene.items() if isinstance(i, CanvasItem)]
        assert len(items) == 2

        scene.undo_stack.undo()
        items = [i for i in scene.items() if isinstance(i, CanvasItem)]
        assert len(items) == 1

        scene.undo_stack.redo()
        items = [i for i in scene.items() if isinstance(i, CanvasItem)]
        assert len(items) == 2

    @pytest.mark.usefixtures("_qapp")
    def test_delete_undo(self, scene) -> None:
        from trcc_vision.adapters.gui.widgets.canvas_scene import CanvasItem

        item = _data_item(scene)
        item.setSelected(True)
        scene.delete_selected()

        items = [i for i in scene.items() if isinstance(i, CanvasItem)]
        assert len(items) == 0

        scene.undo_stack.undo()
        items = [i for i in scene.items() if isinstance(i, CanvasItem)]
        assert len(items) == 1


class TestZOrderCommand:
    @pytest.mark.usefixtures("_qapp")
    def test_z_order_undo(self, scene) -> None:
        item = _data_item(scene)
        item.setSelected(True)
        assert item.element.z_index == 5

        scene.change_z_order(3)
        assert item.element.z_index == 8
        assert item.zValue() == 8

        scene.undo_stack.undo()
        assert item.element.z_index == 5
        assert item.zValue() == 5


class TestPropertyChangeCommand:
    @pytest.mark.usefixtures("_qapp")
    def test_property_undo(self, scene) -> None:
        from trcc_vision.adapters.gui.widgets.undo_commands import PropertyChangeCommand

        item = _data_item(scene)
        cmd = PropertyChangeCommand(item, "color", "#FFFFFF", "#FF0000")
        cmd.redo()
        assert item.element.color == "#FF0000"

        cmd.undo()
        assert item.element.color == "#FFFFFF"
