"""Theme card widget — thumbnail preview with selection highlight.

Matches C# UCCard: preview image + name label, 2px border when selected.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCursor, QPixmap
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from trcc_vision.adapters.gui.constants import THEME_CARD_HEIGHT, THEME_CARD_WIDTH

if TYPE_CHECKING:
    from pathlib import Path

log = logging.getLogger(__name__)


class ThemeCard(QWidget):
    """Clickable theme thumbnail with name and selection state."""

    selected_signal = Signal(str)  # emits theme name

    def __init__(
        self,
        name: str,
        preview_path: Path | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._name = name
        self._is_selected = False

        self.setFixedSize(THEME_CARD_WIDTH, THEME_CARD_HEIGHT)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._update_style()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Preview image
        self._preview = QLabel()
        self._preview.setFixedSize(THEME_CARD_WIDTH - 8, THEME_CARD_HEIGHT - 30)
        self._preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview.setStyleSheet("background: #1a1a2e; border-radius: 4px;")

        if preview_path and preview_path.exists():
            pixmap = QPixmap(str(preview_path))
            if not pixmap.isNull():
                scaled = pixmap.scaled(
                    THEME_CARD_WIDTH - 8, THEME_CARD_HEIGHT - 30,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                self._preview.setPixmap(scaled)

        layout.addWidget(self._preview)

        # Name label
        self._label = QLabel(name)
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setStyleSheet(
            "color: #cccccc; font-size: 11px; background: transparent;"
        )
        layout.addWidget(self._label)

    @property
    def theme_name(self) -> str:
        return self._name

    @property
    def is_selected(self) -> bool:
        return self._is_selected

    def set_selected(self, selected: bool) -> None:
        """Update selection state with visual feedback."""
        self._is_selected = selected
        self._update_style()

    def mousePressEvent(self, event) -> None:  # noqa: ANN001
        if event.button() == Qt.MouseButton.LeftButton:
            self.selected_signal.emit(self._name)

    def _update_style(self) -> None:
        if self._is_selected:
            self.setStyleSheet(
                "ThemeCard { border: 2px solid #00aaff; border-radius: 6px; "
                "background: rgba(0, 170, 255, 30); }"
            )
        else:
            self.setStyleSheet(
                "ThemeCard { border: 1px solid #444466; border-radius: 6px; "
                "background: rgba(30, 30, 50, 150); }"
            )
