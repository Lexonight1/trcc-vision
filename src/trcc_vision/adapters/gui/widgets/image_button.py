"""Image button — clickable PNG label with no Qt button chrome.

Used for close, minimize, navigation tabs, apply, and all image-based
buttons in the frameless window. Matches the C# WPF pattern of using
Image controls with click handlers instead of standard buttons.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCursor, QPixmap
from PySide6.QtWidgets import QLabel

if TYPE_CHECKING:
    from pathlib import Path

    from PySide6.QtWidgets import QWidget

log = logging.getLogger(__name__)


class ImageButton(QLabel):
    """A clickable image label — no standard button styling."""

    clicked = Signal()

    def __init__(
        self,
        image_path: Path,
        parent: QWidget | None = None,
        *,
        tooltip: str = "",
        hover_opacity: float = 0.8,
    ) -> None:
        super().__init__(parent)
        self._hover_opacity = hover_opacity
        self._normal_opacity = 1.0

        pixmap = QPixmap(str(image_path))
        if pixmap.isNull():
            log.warning("Failed to load image: %s", image_path)
        else:
            self.setPixmap(pixmap)
            self.setFixedSize(pixmap.size())

        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setStyleSheet("background: transparent;")

        if tooltip:
            self.setToolTip(tooltip)

        log.debug("ImageButton created: %s", getattr(image_path, "name", image_path))

    def mousePressEvent(self, event) -> None:  # noqa: ANN001
        """Emit clicked signal on left click."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
            log.debug("ImageButton clicked")

    def enterEvent(self, event) -> None:  # noqa: ANN001
        """Reduce opacity on hover."""
        self.setWindowOpacity(self._hover_opacity)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: ANN001
        """Restore opacity on leave."""
        self.setWindowOpacity(self._normal_opacity)
        super().leaveEvent(event)
