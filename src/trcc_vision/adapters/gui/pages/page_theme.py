"""Theme browser page — theme list + LCD preview.

Matches C# PageYJ theme section: WrapPanel of ThemeCards on left,
480x480 preview on right, apply/delete buttons at bottom.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from trcc_vision.adapters.gui.constants import GUI_ASSETS, THEME_ASSETS
from trcc_vision.adapters.gui.widgets.image_button import ImageButton
from trcc_vision.adapters.gui.widgets.lcd_preview import LCDPreview
from trcc_vision.adapters.gui.widgets.theme_card import ThemeCard
from trcc_vision.core.events import SensorUpdated
from trcc_vision.infrastructure.i18n import t
from trcc_vision.infrastructure.theme_xml_parser import ThemeXmlParser

if TYPE_CHECKING:
    from trcc_vision.core.context import AppContext
    from trcc_vision.core.models import ThemeConfig, ThemeInfo

log = logging.getLogger(__name__)


class PageTheme(QWidget):
    """Theme browser with preview and selection."""

    edit_requested = Signal(object, object)  # (ThemeInfo, ThemeConfig)

    def __init__(self, ctx: AppContext) -> None:
        super().__init__()
        self._ctx = ctx
        self._parser = ThemeXmlParser()
        self._cards: list[ThemeCard] = []
        self._selected_theme: str | None = None
        self._selected_theme_info: ThemeInfo | None = None
        self._selected_config: ThemeConfig | None = None

        self.setStyleSheet("background: transparent;")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)

        # Left: theme list
        self._setup_theme_list(layout)

        # Right: preview + controls
        self._setup_preview(layout)

        # Subscribe to sensor updates for live preview
        ctx.event_bus.subscribe(SensorUpdated, self._on_sensor_updated)

        log.info("PageTheme created")

    def _setup_theme_list(self, parent: QHBoxLayout) -> None:
        """Left panel — scrollable theme card grid."""
        left = QWidget()
        left.setFixedWidth(500)
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(10, 0, 0, 0)

        title = QLabel(t("gui.theme.theme_list"))
        title.setStyleSheet(
            "color: white; font-size: 16px; font-weight: bold; background: transparent;"
        )
        left_layout.addWidget(title)

        # Scroll area with theme cards
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
            "QScrollBar:vertical { background: #2a2a3e; width: 8px; }"
            "QScrollBar::handle:vertical { background: #555577; border-radius: 4px; }"
        )

        card_container = QWidget()
        card_container.setStyleSheet("background: transparent;")
        self._card_grid = QGridLayout(card_container)
        self._card_grid.setSpacing(8)
        self._card_grid.setContentsMargins(5, 5, 5, 5)

        # Load default themes
        self._load_default_themes()

        scroll.setWidget(card_container)
        left_layout.addWidget(scroll, 1)

        parent.addWidget(left)

    def _setup_preview(self, parent: QHBoxLayout) -> None:
        """Right panel — LCD preview + action buttons."""
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 10, 0)

        title = QLabel(t("gui.theme.theme_preview"))
        title.setStyleSheet(
            "color: white; font-size: 16px; font-weight: bold; background: transparent;"
        )
        right_layout.addWidget(title)

        # LCD preview
        self._preview = LCDPreview()
        right_layout.addWidget(self._preview, 0, Qt.AlignmentFlag.AlignCenter)

        # Action buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        apply_btn = ImageButton(
            GUI_ASSETS / "btn_apply.png", tooltip=t("gui.btn.apply"),
        )
        apply_btn.clicked.connect(self._on_apply)
        btn_row.addWidget(apply_btn)

        edit_btn = ImageButton(
            GUI_ASSETS / "btn_ok.png", tooltip=t("gui.btn.edit"),
        )
        edit_btn.clicked.connect(self._on_edit)
        btn_row.addWidget(edit_btn)

        btn_row.addStretch()
        right_layout.addLayout(btn_row)
        right_layout.addStretch()

        parent.addWidget(right, 1)

    def _load_default_themes(self) -> None:
        """Load the 10 bundled default themes as cards."""
        cols = 3

        for i in range(1, 11):
            xml_path = THEME_ASSETS / f"Theme{i}.xml"
            preview_path = THEME_ASSETS / f"Theme{i}.png"

            if not xml_path.exists():
                continue

            name = t(f"gui.theme.theme_{i}")
            card = ThemeCard(
                name=name,
                preview_path=preview_path if preview_path.exists() else None,
            )
            card.selected_signal.connect(self._on_theme_selected)
            self._cards.append(card)

            row = (i - 1) // cols
            col = (i - 1) % cols
            self._card_grid.addWidget(card, row, col)

        log.info("Loaded %d default theme cards", len(self._cards))

    def _on_theme_selected(self, name: str) -> None:
        """Handle theme card click."""
        log.info("Theme selected: %s", name)
        self._selected_theme = name

        # Update card selection state
        for card in self._cards:
            card.set_selected(card.theme_name == name)

        # Load theme via use case (ThemeService → ThemeRepositoryPort → XML parser)
        for i in range(1, 21):
            if t(f"gui.theme.theme_{i}") == name:
                xml_path = THEME_ASSETS / f"Theme{i}.xml"
                if not xml_path.exists():
                    break
                from trcc_vision.core.models import ThemeInfo as TI
                theme_info = TI(name=name, path=xml_path)
                if self._ctx.load_theme:
                    config = self._ctx.load_theme.execute(theme_info)
                else:
                    config = self._parser.parse(xml_path)
                self._selected_theme_info = theme_info
                self._selected_config = config
                self._preview.set_theme(config)
                break

    def _on_edit(self) -> None:
        """Open the theme editor for the selected theme."""
        if not self._selected_theme_info or not self._selected_config:
            log.warning("No theme selected to edit")
            return
        log.info("Edit requested for: %s", self._selected_theme_info.name)
        self.edit_requested.emit(self._selected_theme_info, self._selected_config)

    def _on_apply(self) -> None:
        """Apply selected theme to device."""
        if not self._selected_theme:
            log.warning("No theme selected to apply")
            return
        log.info("Applying theme: %s", self._selected_theme)
        # TODO: send theme to device via use case

    def _on_sensor_updated(self, event: SensorUpdated) -> None:
        """Update LCD preview with live sensor data."""
        self._preview.update_sensors(event.readings)
