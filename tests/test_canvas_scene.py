"""Tests for the theme editor canvas scene and items."""

from __future__ import annotations

import pytest

from trcc_vision.core.enums import ElementType, TimerFormat
from trcc_vision.core.models import DataItem, ThemeConfig, ThemeElement


@pytest.fixture()
def _qapp():
    """Ensure a QApplication exists for QGraphicsScene tests."""
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture()
def sample_config() -> ThemeConfig:
    return ThemeConfig(
        name="Test Theme",
        theme_type="CustomTheme",
        elements=[
            ThemeElement(
                element_type=ElementType.IMAGE,
                image_file_path="20240417095652723.png",
                x=0, y=0, width=480, height=480, z_index=0,
            ),
            ThemeElement(
                element_type=ElementType.DATA,
                content="42",
                data_item=DataItem(data_num=0, name="CPU Temp"),
                data_unit="°C",
                x=100.0, y=200.0, z_index=2,
                font_size=48.0, color="#FF0000",
            ),
            ThemeElement(
                element_type=ElementType.TIMER,
                timer_type=TimerFormat.TIME,
                x=50.0, y=350.0, z_index=3,
                font_size=32.0, color="#00FF00",
            ),
        ],
    )


class TestEditorScene:
    @pytest.mark.usefixtures("_qapp")
    def test_load_config_creates_items(self, sample_config: ThemeConfig) -> None:
        from trcc_vision.adapters.gui.widgets.canvas_scene import EditorScene

        scene = EditorScene()
        scene.load_config(sample_config)

        # 3 elements → 3 canvas items
        from trcc_vision.adapters.gui.widgets.canvas_scene import CanvasItem

        items = [i for i in scene.items() if isinstance(i, CanvasItem)]
        assert len(items) == 3

    @pytest.mark.usefixtures("_qapp")
    def test_extract_config_preserves_metadata(self, sample_config: ThemeConfig) -> None:
        from trcc_vision.adapters.gui.widgets.canvas_scene import EditorScene

        scene = EditorScene()
        scene.load_config(sample_config)

        result = scene.extract_config()
        assert result.name == "Test Theme"
        assert result.theme_type == "CustomTheme"
        assert len(result.elements) == 3

    @pytest.mark.usefixtures("_qapp")
    def test_extract_config_roundtrip_positions(self, sample_config: ThemeConfig) -> None:
        from trcc_vision.adapters.gui.widgets.canvas_scene import CanvasItem, EditorScene

        scene = EditorScene()
        scene.load_config(sample_config)

        # Move the DATA item
        data_items = [
            i for i in scene.items()
            if isinstance(i, CanvasItem)
            and i.element.element_type == ElementType.DATA
        ]
        assert len(data_items) == 1
        data_items[0].setPos(150, 250)

        result = scene.extract_config()
        data_elem = next(e for e in result.elements if e.element_type == ElementType.DATA)
        assert abs(data_elem.x - 150) < 0.1
        assert abs(data_elem.y - 250) < 0.1

    @pytest.mark.usefixtures("_qapp")
    def test_z_ordering_matches_model(self, sample_config: ThemeConfig) -> None:
        from trcc_vision.adapters.gui.widgets.canvas_scene import CanvasItem, EditorScene

        scene = EditorScene()
        scene.load_config(sample_config)

        for item in scene.items():
            if isinstance(item, CanvasItem):
                assert item.zValue() == item.element.z_index

    @pytest.mark.usefixtures("_qapp")
    def test_add_element(self) -> None:
        from trcc_vision.adapters.gui.widgets.canvas_scene import CanvasItem, EditorScene

        scene = EditorScene()
        scene.load_config(ThemeConfig(name="Empty"))

        elem = ThemeElement(
            element_type=ElementType.DATA,
            content="0", x=100, y=100, font_size=24.0,
            data_item=DataItem(data_num=0, name="Test"),
        )
        item = scene.add_element(elem)
        assert isinstance(item, CanvasItem)

        items = [i for i in scene.items() if isinstance(i, CanvasItem)]
        assert len(items) == 1

    @pytest.mark.usefixtures("_qapp")
    def test_delete_selected(self, sample_config: ThemeConfig) -> None:
        from trcc_vision.adapters.gui.widgets.canvas_scene import CanvasItem, EditorScene

        scene = EditorScene()
        scene.load_config(sample_config)

        # Select and delete the DATA item
        for item in scene.items():
            if isinstance(item, CanvasItem) and item.element.element_type == ElementType.DATA:
                item.setSelected(True)
                break

        deleted = scene.delete_selected()
        assert len(deleted) == 1
        assert deleted[0].element_type == ElementType.DATA

        remaining = [i for i in scene.items() if isinstance(i, CanvasItem)]
        assert len(remaining) == 2

    @pytest.mark.usefixtures("_qapp")
    def test_duplicate_selected(self, sample_config: ThemeConfig) -> None:
        from trcc_vision.adapters.gui.widgets.canvas_scene import CanvasItem, EditorScene

        scene = EditorScene()
        scene.load_config(sample_config)

        # Select the TIMER item
        for item in scene.items():
            if isinstance(item, CanvasItem) and item.element.element_type == ElementType.TIMER:
                item.setSelected(True)
                break

        new_items = scene.duplicate_selected()
        assert len(new_items) == 1
        assert new_items[0].element.element_type == ElementType.TIMER
        # Duplicate should be offset
        assert abs(new_items[0].element.x - 70) < 0.1  # 50 + 20

    @pytest.mark.usefixtures("_qapp")
    def test_change_z_order(self, sample_config: ThemeConfig) -> None:
        from trcc_vision.adapters.gui.widgets.canvas_scene import CanvasItem, EditorScene

        scene = EditorScene()
        scene.load_config(sample_config)

        # Select the DATA item (z=2) and bring forward
        for item in scene.items():
            if isinstance(item, CanvasItem) and item.element.element_type == ElementType.DATA:
                item.setSelected(True)
                break

        scene.change_z_order(5)

        for item in scene.items():
            if isinstance(item, CanvasItem) and item.element.element_type == ElementType.DATA:
                assert item.element.z_index == 7
                assert item.zValue() == 7


class TestCanvasItems:
    @pytest.mark.usefixtures("_qapp")
    def test_text_item_position_sync(self) -> None:
        from trcc_vision.adapters.gui.widgets.canvas_scene import TextItem

        elem = ThemeElement(
            element_type=ElementType.DATA,
            content="42", x=100, y=200, font_size=24.0,
            data_item=DataItem(data_num=0, name="CPU"),
        )
        item = TextItem(elem)
        item.setPos(150, 250)

        # itemChange syncs position back to element
        assert abs(elem.x - 150) < 0.1
        assert abs(elem.y - 250) < 0.1

    @pytest.mark.usefixtures("_qapp")
    def test_text_item_bounding_rect_nonzero(self) -> None:
        from trcc_vision.adapters.gui.widgets.canvas_scene import TextItem

        elem = ThemeElement(
            element_type=ElementType.DATA,
            content="42°C", x=0, y=0, font_size=48.0,
            data_item=DataItem(data_num=0, name="CPU"),
        )
        item = TextItem(elem)
        rect = item.boundingRect()
        assert rect.width() > 0
        assert rect.height() > 0

    @pytest.mark.usefixtures("_qapp")
    def test_image_item_bounding_rect(self) -> None:
        from trcc_vision.adapters.gui.widgets.canvas_scene import ImageItem

        elem = ThemeElement(
            element_type=ElementType.IMAGE,
            image_file_path="20240417095652723.png",
            x=0, y=0, width=480, height=480,
        )
        item = ImageItem(elem)
        rect = item.boundingRect()
        # Should be 480x480 (scaled to LCD size) or placeholder size
        assert rect.width() > 0
        assert rect.height() > 0

    @pytest.mark.usefixtures("_qapp")
    def test_update_display_text(self) -> None:
        from trcc_vision.adapters.gui.widgets.canvas_scene import TextItem

        elem = ThemeElement(
            element_type=ElementType.DATA,
            content="0", x=0, y=0, font_size=24.0,
            data_item=DataItem(data_num=0, name="CPU"),
        )
        item = TextItem(elem)
        item.update_display_text("65°C")
        assert item._display_text == "65°C"
