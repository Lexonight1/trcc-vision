"""Theme XML parser — parse/serialize Theme*.xml files.

Uses stdlib xml.etree.ElementTree (zero deps). Handles the full
ThemeModel schema from TR-VISION HOME default themes.
"""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from typing import TYPE_CHECKING

from trcc_vision.core.enums import ElementType, FontType, TimerFormat
from trcc_vision.core.models import DataItem, ThemeConfig, ThemeElement

if TYPE_CHECKING:
    from pathlib import Path

log = logging.getLogger(__name__)


def _text(node: ET.Element, tag: str, default: str = "") -> str:
    """Get text content of a child element, or default."""
    child = node.find(tag)
    if child is not None and child.text:
        return child.text.strip()
    return default


def _int(node: ET.Element, tag: str, default: int = 0) -> int:
    """Get int content of a child element, or default."""
    raw = _text(node, tag)
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        try:
            return int(float(raw))
        except ValueError:
            log.warning("Cannot parse int from <%s>: %r", tag, raw)
            return default


def _float(node: ET.Element, tag: str, default: float = 0.0) -> float:
    """Get float content of a child element, or default."""
    raw = _text(node, tag)
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        log.warning("Cannot parse float from <%s>: %r", tag, raw)
        return default


def _bool(node: ET.Element, tag: str, default: bool = False) -> bool:
    """Get bool content of a child element, or default."""
    raw = _text(node, tag).lower()
    if raw in ("true", "1"):
        return True
    if raw in ("false", "0"):
        return False
    return default


class ThemeXmlParser:
    """Parse and serialize TR-VISION Theme*.xml files."""

    def parse(self, xml_path: Path) -> ThemeConfig:
        """Parse a theme XML file into a ThemeConfig."""
        log.debug("Parsing theme XML: %s", xml_path)
        tree = ET.parse(xml_path)  # noqa: S314
        return self._parse_root(tree.getroot())

    def parse_bytes(self, data: bytes) -> ThemeConfig:
        """Parse theme XML from raw bytes."""
        log.debug("Parsing theme XML from %d bytes", len(data))
        root = ET.fromstring(data)  # noqa: S314
        return self._parse_root(root)

    def serialize(self, config: ThemeConfig, xml_path: Path) -> None:
        """Write a ThemeConfig to an XML file."""
        log.debug("Serializing theme XML: %s", xml_path)
        root = self._build_root(config)
        tree = ET.ElementTree(root)
        ET.indent(tree, space="\t")
        tree.write(xml_path, encoding="utf-8", xml_declaration=True)
        log.info("Theme saved: %s (%d elements)", xml_path.name, len(config.elements))

    def serialize_bytes(self, config: ThemeConfig) -> bytes:
        """Serialize a ThemeConfig to XML bytes."""
        root = self._build_root(config)
        ET.indent(root, space="\t")
        return ET.tostring(root, encoding="utf-8", xml_declaration=True)

    # ── Parse ───────────────────────────────────────────────────────────

    def _parse_root(self, root: ET.Element) -> ThemeConfig:
        """Parse the <ThemeModel> root element."""
        elements: list[ThemeElement] = []
        elements_node = root.find("ThemeElements")
        if elements_node is not None:
            for elem_node in elements_node.findall("ThemeElement"):
                elem = self._parse_element(elem_node)
                if elem:
                    elements.append(elem)

        config = ThemeConfig(
            name=_text(root, "Name"),
            theme_type=_text(root, "ThemeType", "DefaultTheme"),
            rotation=_int(root, "Rotate"),
            elements=elements,
            display_data=_bool(root, "DisplayData", True),
            display_timer=_bool(root, "DisplayTimer", True),
            display_image=_bool(root, "DisplayImage", True),
            display_video=_bool(root, "DisplayVideo", False),
            display_text_block=_bool(root, "DisplayUCTextBlock", False),
        )
        log.info(
            "Parsed theme '%s': %d elements (D=%d T=%d I=%d V=%d)",
            config.name, len(elements),
            sum(1 for e in elements if e.element_type == ElementType.DATA),
            sum(1 for e in elements if e.element_type == ElementType.TIMER),
            sum(1 for e in elements if e.element_type == ElementType.IMAGE),
            sum(1 for e in elements if e.element_type == ElementType.VIDEO),
        )
        return config

    def _parse_element(self, node: ET.Element) -> ThemeElement | None:
        """Parse a single <ThemeElement>."""
        raw_type = _text(node, "ElementType")
        try:
            element_type = ElementType(raw_type)
        except ValueError:
            log.warning("Unknown ElementType: %r — skipping", raw_type)
            return None

        data_item = self._parse_data_item(node)

        raw_timer = _int(node, "TimerType")
        try:
            timer_type = TimerFormat(raw_timer)
        except ValueError:
            timer_type = TimerFormat.TIME

        raw_font_type = _text(node, "FontType", "Default")
        try:
            font_type = FontType(raw_font_type)
        except ValueError:
            font_type = FontType.DEFAULT

        color = _text(node, "ColorString", "#FFFFFF")
        if not color.startswith("#"):
            color = "#FFFFFF"

        return ThemeElement(
            element_type=element_type,
            content=_text(node, "Content"),
            data_item=data_item,
            data_unit=_text(node, "DataUnit"),
            show_data_type_name=_bool(node, "ShowDataTypeName"),
            timer_type=timer_type,
            image_file_path=_text(node, "ImageFilePath"),
            video_file=_text(node, "VideoFile"),
            play_count=_int(node, "PlayCount"),
            x=_float(node, "X"),
            y=_float(node, "Y"),
            width=_int(node, "Width"),
            height=_int(node, "Height"),
            scale_x=_float(node, "ScaleX", 1.0),
            scale_y=_float(node, "ScaleY", 1.0),
            z_index=_int(node, "ZIndex"),
            font_family=_text(node, "FontFamily", "NI7SEG"),
            font_size=_float(node, "FontSize", 20.0),
            font_type=font_type,
            font_file_name=_text(node, "FontFileName"),
            font_weight=_bool(node, "FontWeight"),
            font_style=_bool(node, "FontStyle"),
            color=color,
            opacity=_float(node, "Opacity", 1.0),
            uc_name=_text(node, "UCName"),
            marquee_type=_int(node, "MarqueeType"),
        )

    def _parse_data_item(self, node: ET.Element) -> DataItem:
        """Parse the nested <DataItem> from an element."""
        di_node = node.find("DataItem")
        if di_node is None:
            return DataItem()
        return DataItem(
            data_num=_int(di_node, "DataNum"),
            name=_text(di_node, "Name"),
        )

    # ── Serialize ───────────────────────────────────────────────────────

    def _build_root(self, config: ThemeConfig) -> ET.Element:
        """Build the <ThemeModel> XML tree."""
        root = ET.Element("ThemeModel")
        ET.SubElement(root, "_rotate").text = str(config.rotation)
        ET.SubElement(root, "Name").text = config.name
        ET.SubElement(root, "ThemeType").text = config.theme_type

        elements_node = ET.SubElement(root, "ThemeElements")
        for elem in config.elements:
            elements_node.append(self._build_element(elem))

        ET.SubElement(root, "DisplayUCTextBlock").text = str(config.display_text_block).lower()
        ET.SubElement(root, "DisplayData").text = str(config.display_data).lower()
        ET.SubElement(root, "DisplayTimer").text = str(config.display_timer).lower()
        ET.SubElement(root, "DisplayImage").text = str(config.display_image).lower()
        ET.SubElement(root, "DisplayVideo").text = str(config.display_video).lower()
        ET.SubElement(root, "Rotate").text = str(config.rotation)
        return root

    def _build_element(self, elem: ThemeElement) -> ET.Element:
        """Build a single <ThemeElement> XML node."""
        node = ET.Element("ThemeElement")

        ET.SubElement(node, "Content").text = elem.content
        ET.SubElement(node, "FontSize").text = str(int(elem.font_size))
        ET.SubElement(node, "MarqueeType").text = str(elem.marquee_type)
        ET.SubElement(node, "DataTypeIndex").text = "0"

        # DataItem
        di = ET.SubElement(node, "DataItem")
        ET.SubElement(di, "DataNum").text = str(elem.data_item.data_num)
        ET.SubElement(di, "Name").text = elem.data_item.name
        ET.SubElement(di, "FileName")

        ET.SubElement(node, "ShowDataTypeName").text = str(elem.show_data_type_name).lower()
        ET.SubElement(node, "TimerType").text = str(elem.timer_type.value)
        ET.SubElement(node, "Width").text = str(elem.width)
        ET.SubElement(node, "Height").text = str(elem.height)
        ET.SubElement(node, "PlayCount").text = str(elem.play_count)
        ET.SubElement(node, "ElementType").text = elem.element_type.value
        ET.SubElement(node, "ImageFilePath").text = elem.image_file_path
        ET.SubElement(node, "ColorString").text = elem.color
        ET.SubElement(node, "ZIndex").text = str(elem.z_index)
        ET.SubElement(node, "DataUnit").text = elem.data_unit
        ET.SubElement(node, "X").text = str(elem.x)
        ET.SubElement(node, "Y").text = str(elem.y)
        ET.SubElement(node, "ScaleX").text = str(elem.scale_x)
        ET.SubElement(node, "ScaleY").text = str(elem.scale_y)
        ET.SubElement(node, "UCName").text = elem.uc_name
        ET.SubElement(node, "FontFamily").text = elem.font_family
        ET.SubElement(node, "FontWeight").text = str(elem.font_weight).lower()
        ET.SubElement(node, "FontStyle").text = str(elem.font_style).lower()
        ET.SubElement(node, "Opacity").text = str(elem.opacity)
        ET.SubElement(node, "FontType").text = elem.font_type.value
        ET.SubElement(node, "FontFileName").text = elem.font_file_name

        if elem.video_file:
            ET.SubElement(node, "VideoFile").text = elem.video_file

        return node
