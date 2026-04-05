"""Tests for theme XML parser — parses real Theme*.xml files and roundtrips."""

from __future__ import annotations

from pathlib import Path

import pytest

from trcc_vision.core.enums import ElementType, FontType, TimerFormat
from trcc_vision.core.models import DataItem, ThemeConfig, ThemeElement
from trcc_vision.infrastructure.theme_xml_parser import ThemeXmlParser

# Path to real bundled theme assets
THEMES_DIR = Path(__file__).resolve().parent.parent / "src" / "trcc_vision" / "assets" / "themes"


@pytest.fixture()
def parser() -> ThemeXmlParser:
    return ThemeXmlParser()


# ── Parse Real Themes ───────────────────────────────────────────────────


class TestParseRealThemes:
    """Parse all 10 bundled default themes."""

    @pytest.mark.parametrize("n", range(1, 11))
    def test_parse_default_theme(self, parser: ThemeXmlParser, n: int) -> None:
        xml_path = THEMES_DIR / f"Theme{n}.xml"
        if not xml_path.exists():
            pytest.skip(f"Theme{n}.xml not found")

        config = parser.parse(xml_path)
        assert config.name != ""
        assert config.theme_type == "DefaultTheme"
        assert len(config.elements) > 0

    def test_theme1_structure(self, parser: ThemeXmlParser) -> None:
        """Theme1 should have Data + Timer + Image elements."""
        xml_path = THEMES_DIR / "Theme1.xml"
        if not xml_path.exists():
            pytest.skip("Theme1.xml not found")

        config = parser.parse(xml_path)
        types = {e.element_type for e in config.elements}
        assert ElementType.DATA in types
        assert ElementType.TIMER in types
        assert ElementType.IMAGE in types

    def test_theme1_data_elements(self, parser: ThemeXmlParser) -> None:
        """Data elements should have sensor bindings."""
        xml_path = THEMES_DIR / "Theme1.xml"
        if not xml_path.exists():
            pytest.skip("Theme1.xml not found")

        config = parser.parse(xml_path)
        data_elems = [e for e in config.elements if e.element_type == ElementType.DATA]
        assert len(data_elems) >= 1
        # First data element is CPU temp (DataNum=0)
        assert data_elems[0].data_item.data_num == 0
        assert data_elems[0].data_unit in ("℃", "%", "MHz")

    def test_theme1_timer_types(self, parser: ThemeXmlParser) -> None:
        """Timer elements should have different TimerType values."""
        xml_path = THEMES_DIR / "Theme1.xml"
        if not xml_path.exists():
            pytest.skip("Theme1.xml not found")

        config = parser.parse(xml_path)
        timer_elems = [e for e in config.elements if e.element_type == ElementType.TIMER]
        timer_types = {e.timer_type for e in timer_elems}
        assert TimerFormat.TIME in timer_types  # HH:MM:SS

    def test_theme_uses_ni7seg_font(self, parser: ThemeXmlParser) -> None:
        """Most themes use the NI7SEG seven-segment display font."""
        xml_path = THEMES_DIR / "Theme1.xml"
        if not xml_path.exists():
            pytest.skip("Theme1.xml not found")

        config = parser.parse(xml_path)
        ni7seg_elems = [e for e in config.elements if e.font_family == "NI7SEG"]
        assert len(ni7seg_elems) >= 1


# ── Parse Bytes ─────────────────────────────────────────────────────────


class TestParseBytes:
    def test_parse_minimal_xml(self, parser: ThemeXmlParser) -> None:
        xml = b"""<?xml version="1.0"?>
        <ThemeModel>
            <Name>Test</Name>
            <ThemeType>CustomTheme</ThemeType>
            <ThemeElements>
                <ThemeElement>
                    <ElementType>Data</ElementType>
                    <Content>50%</Content>
                    <FontSize>24</FontSize>
                    <ColorString>#FF0000</ColorString>
                    <X>100</X>
                    <Y>200</Y>
                </ThemeElement>
            </ThemeElements>
            <DisplayData>true</DisplayData>
            <DisplayTimer>false</DisplayTimer>
            <DisplayImage>false</DisplayImage>
            <DisplayVideo>false</DisplayVideo>
            <Rotate>0</Rotate>
        </ThemeModel>"""

        config = parser.parse_bytes(xml)
        assert config.name == "Test"
        assert config.theme_type == "CustomTheme"
        assert len(config.elements) == 1
        assert config.elements[0].element_type == ElementType.DATA
        assert config.elements[0].content == "50%"
        assert config.elements[0].color == "#FF0000"
        assert config.elements[0].x == 100.0
        assert config.elements[0].y == 200.0

    def test_unknown_element_type_skipped(self, parser: ThemeXmlParser) -> None:
        xml = b"""<?xml version="1.0"?>
        <ThemeModel>
            <Name>Test</Name>
            <ThemeElements>
                <ThemeElement><ElementType>Unknown</ElementType></ThemeElement>
                <ThemeElement><ElementType>Data</ElementType><FontSize>20</FontSize></ThemeElement>
            </ThemeElements>
        </ThemeModel>"""

        config = parser.parse_bytes(xml)
        assert len(config.elements) == 1
        assert config.elements[0].element_type == ElementType.DATA


# ── Roundtrip ───────────────────────────────────────────────────────────


class TestRoundtrip:
    def test_serialize_then_parse(self, parser: ThemeXmlParser) -> None:
        original = ThemeConfig(
            name="Roundtrip Test",
            theme_type="CustomTheme",
            rotation=90,
            elements=[
                ThemeElement(
                    element_type=ElementType.DATA,
                    content="55℃",
                    data_item=DataItem(data_num=0, name="CPU Temperature"),
                    data_unit="℃",
                    x=100.5,
                    y=200.3,
                    font_family="NI7SEG",
                    font_size=48.0,
                    font_type=FontType.CUSTOM,
                    font_file_name="NI7SEG.TTF",
                    color="#000000",
                    z_index=3,
                ),
                ThemeElement(
                    element_type=ElementType.IMAGE,
                    image_file_path="bg.png",
                    width=480,
                    height=480,
                    z_index=0,
                    color="#FFFFFF",
                ),
            ],
            display_data=True,
            display_timer=False,
            display_image=True,
        )

        xml_bytes = parser.serialize_bytes(original)
        parsed = parser.parse_bytes(xml_bytes)

        assert parsed.name == original.name
        assert parsed.theme_type == original.theme_type
        assert parsed.rotation == original.rotation
        assert len(parsed.elements) == len(original.elements)

        # Check first element (Data)
        p0 = parsed.elements[0]
        assert p0.element_type == ElementType.DATA
        assert p0.content == "55℃"
        assert p0.data_item.data_num == 0
        assert p0.x == 100.5
        assert p0.font_family == "NI7SEG"
        assert p0.color == "#000000"

        # Check second element (Image)
        p1 = parsed.elements[1]
        assert p1.element_type == ElementType.IMAGE
        assert p1.image_file_path == "bg.png"
        assert p1.width == 480

    def test_roundtrip_real_theme(self, parser: ThemeXmlParser) -> None:
        """Parse a real theme, serialize, re-parse — data should survive."""
        xml_path = THEMES_DIR / "Theme1.xml"
        if not xml_path.exists():
            pytest.skip("Theme1.xml not found")

        original = parser.parse(xml_path)
        xml_bytes = parser.serialize_bytes(original)
        reparsed = parser.parse_bytes(xml_bytes)

        assert reparsed.name == original.name
        assert len(reparsed.elements) == len(original.elements)
        for orig_e, repr_e in zip(original.elements, reparsed.elements, strict=False):
            assert orig_e.element_type == repr_e.element_type
            assert orig_e.x == repr_e.x
            assert orig_e.y == repr_e.y
            assert orig_e.color == repr_e.color


# ── Asset Loader ────────────────────────────────────────────────────────


class TestAssetLoader:
    def test_list_fonts(self) -> None:
        from trcc_vision.infrastructure.asset_loader import AssetLoader

        loader = AssetLoader()
        fonts = loader.list_fonts()
        assert len(fonts) >= 6  # at least the bundled ones
        names = [f.name for f in fonts]
        assert "NI7SEG" in names

    def test_get_font_path_bundled(self) -> None:
        from trcc_vision.infrastructure.asset_loader import AssetLoader

        loader = AssetLoader()
        path = loader.get_font_path("NI7SEG.TTF")
        assert path is not None
        assert path.exists()

    def test_get_font_path_missing(self) -> None:
        from trcc_vision.infrastructure.asset_loader import AssetLoader

        loader = AssetLoader()
        assert loader.get_font_path("nonexistent.ttf") is None

    def test_list_theme_xmls(self) -> None:
        from trcc_vision.infrastructure.asset_loader import AssetLoader

        loader = AssetLoader()
        themes = loader.list_theme_dirs()
        assert len(themes) >= 1  # at least Theme1.xml
