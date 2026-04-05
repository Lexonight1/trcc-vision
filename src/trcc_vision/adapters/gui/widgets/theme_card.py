"""Theme card widget — small thumbnail with selection highlight.

Matches C# UCCard XAML: 60x60 Border with white border, CornerRadius=5,
30x30 image centered + 9pt label below.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCursor, QPixmap
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from trcc_vision.adapters.gui.constants import (
    THEME_CARD_HEIGHT,
    THEME_CARD_IMAGE,
    THEME_CARD_WIDTH,
)

if TYPE_CHECKING:
    from pathlib import Path

log = logging.getLogger(__name__)


class ThemeCard(QWidget):
    """Clickable theme thumbnail (60x60) with name and selection state."""

    selected_signal = Signal(str)

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
        layout.setContentsMargins(2, 3, 2, 1)
        layout.setSpacing(1)

        # 30x30 preview image
        self._preview = QLabel()
        self._preview.setFixedSize(THEME_CARD_IMAGE, THEME_CARD_IMAGE)
        self._preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview.setStyleSheet("background: transparent;")
        self._preview.setScaledContents(True)

        if preview_path and preview_path.exists():
            pixmap = QPixmap(str(preview_path))
            if not pixmap.isNull():
                self._preview.setPixmap(pixmap.scaled(
                    THEME_CARD_IMAGE, THEME_CARD_IMAGE,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                ))

        layout.addWidget(self._preview, 0, Qt.AlignmentFlag.AlignCenter)

        # Name label (font 9, white)
        self._label = QLabel(name)
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setStyleSheet(
            "color: white; font-size: 9px; background: transparent;"
        )
        self._label.setMaximumWidth(THEME_CARD_WIDTH - 4)
        layout.addWidget(self._label)

    @property
    def theme_name(self) -> str:
        return self._name

    @property
    def is_selected(self) -> bool:
        return self._is_selected

    def set_selected(self, selected: bool) -> None:
        self._is_selected = selected
        self._update_style()

    def mousePressEvent(self, event) -> None:  # noqa: ANN001
        if event.button() == Qt.MouseButton.LeftButton:
            self.selected_signal.emit(self._name)

    def _update_style(self) -> None:
        # XAML: BorderBrush="White" BorderThickness="1" CornerRadius="5"
        if self._is_selected:
            self.setStyleSheet(
                "ThemeCard { border: 2px solid #847148; border-radius: 5px; "
                "background: rgba(132, 113, 72, 50); }"
            )
        else:
            self.setStyleSheet(
                "ThemeCard { border: 1px solid white; border-radius: 5px; "
                "background: transparent; }"
            )
