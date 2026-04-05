"""Frameless main window — image-based chrome with page navigation.

Matches the C# MainWindow: WindowStyle=None, AllowsTransparency=True,
1400x800 fixed size, bg_main.png background, Frame-based page switching.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QLabel,
    QMainWindow,
    QStackedWidget,
    QWidget,
)

from trcc_vision.adapters.gui.constants import (
    BTN_CLOSE_X,
    BTN_CLOSE_Y,
    BTN_MIN_X,
    BTN_MIN_Y,
    CONTENT_HEIGHT,
    CONTENT_WIDTH,
    CONTENT_X,
    CONTENT_Y,
    DEVICE_STATUS_X,
    DEVICE_STATUS_Y,
    GUI_ASSETS,
    NAV_TAB_HEIGHT,
    NAV_TAB_SPACING,
    NAV_TAB_WIDTH,
    NAV_TABS,
    NAV_X_START,
    NAV_Y,
    TITLEBAR_HEIGHT,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
)
from trcc_vision.adapters.gui.widgets.image_button import ImageButton
from trcc_vision.infrastructure.i18n import t

if TYPE_CHECKING:
    from PySide6.QtGui import QMouseEvent

    from trcc_vision.core.context import AppContext

log = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Frameless image-based main window with tab navigation."""

    def __init__(self, ctx: AppContext) -> None:
        super().__init__()
        self._ctx = ctx
        self._drag_pos: QPoint | None = None

        # Frameless + transparent (matching C# WindowStyle=None)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.setWindowTitle(t("app.name"))

        # Root widget — all children positioned absolutely on this
        self._root = QWidget(self)
        self._root.setFixedSize(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.setCentralWidget(self._root)

        self._setup_background()
        self._setup_titlebar()
        self._setup_navigation()
        self._setup_pages()

        # Subscribe to device events for status icon updates
        from trcc_vision.core.events import DeviceConnected, DeviceDisconnected
        ctx.event_bus.subscribe(DeviceConnected, lambda _: self._update_device_status())
        ctx.event_bus.subscribe(DeviceDisconnected, lambda _: self._update_device_status())

        # Default to hardware page
        self._select_tab(0)

        log.info("MainWindow created: %dx%d frameless", WINDOW_WIDTH, WINDOW_HEIGHT)

    # ── Background ──────────────────────────────────────────────────

    def _setup_background(self) -> None:
        """Set the main background image."""
        bg_path = GUI_ASSETS / "bg_main.png"
        bg_label = QLabel(self._root)
        pixmap = QPixmap(str(bg_path))
        if not pixmap.isNull():
            # Scale to window size (bg is 1619x947, window is 1400x800)
            scaled = pixmap.scaled(
                WINDOW_WIDTH, WINDOW_HEIGHT,
                Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            bg_label.setPixmap(scaled)
        else:
            log.warning("Background image not found: %s", bg_path)
            bg_label.setStyleSheet("background-color: #1a1a2e;")
        bg_label.setGeometry(0, 0, WINDOW_WIDTH, WINDOW_HEIGHT)
        bg_label.lower()  # send to back

    # ── Title bar ───────────────────────────────────────────────────

    def _setup_titlebar(self) -> None:
        """Create close/minimize buttons and device status indicator."""
        # Close button
        close_path = GUI_ASSETS / "btn_close.png"
        self._btn_close = ImageButton(close_path, self._root, tooltip=t("gui.btn.exit"))
        self._btn_close.move(BTN_CLOSE_X, BTN_CLOSE_Y)
        self._btn_close.clicked.connect(self.close)

        # Minimize button
        min_path = GUI_ASSETS / "btn_minimize.png"
        self._btn_min = ImageButton(min_path, self._root, tooltip=t("gui.btn.cancel"))
        self._btn_min.move(BTN_MIN_X, BTN_MIN_Y)
        self._btn_min.clicked.connect(self.showMinimized)

        # Device status indicator
        self._device_status = QLabel(self._root)
        self._update_device_status()
        self._device_status.move(DEVICE_STATUS_X, DEVICE_STATUS_Y)

        # App title
        title = QLabel(t("app.name"), self._root)
        title.setStyleSheet(
            "color: white; font-size: 16px; font-weight: bold; background: transparent;"
        )
        title.move(30, 22)

    def _update_device_status(self) -> None:
        """Update the device connection indicator."""
        if self._ctx.mock or (
            self._ctx.get_device_status
            and self._ctx.get_device_status.execute().connected
        ):
            icon = GUI_ASSETS / "icon_connected.png"
            tip = t("gui.device.connected")
        else:
            icon = GUI_ASSETS / "icon_disconnected.png"
            tip = t("gui.device.disconnected")

        pixmap = QPixmap(str(icon))
        if not pixmap.isNull():
            self._device_status.setPixmap(pixmap)
            self._device_status.setFixedSize(pixmap.size())
        self._device_status.setToolTip(tip)
        self._device_status.setStyleSheet("background: transparent;")

    # ── Navigation tabs ─────────────────────────────────────────────

    def _setup_navigation(self) -> None:
        """Create the 3 navigation tab buttons."""
        self._tab_buttons: list[ImageButton] = []
        self._tab_labels: list[QLabel] = []

        for i, tab in enumerate(NAV_TABS):
            x = NAV_X_START + i * (NAV_TAB_WIDTH + NAV_TAB_SPACING)

            # Tab background (btn_tab_inactive.png)
            btn = ImageButton(
                GUI_ASSETS / "btn_tab_inactive.png",
                self._root,
                tooltip=t(tab["label"]),
            )
            btn.move(x, NAV_Y)
            btn.clicked.connect(lambda idx=i: self._select_tab(idx))
            self._tab_buttons.append(btn)

            # Tab icon + label overlay
            label = QLabel(self._root)
            label.setText(f"  {t(tab['label'])}")
            label.setStyleSheet(
                "color: white; font-size: 13px; background: transparent;"
            )
            label.setGeometry(x + 10, NAV_Y + 5, NAV_TAB_WIDTH - 20, NAV_TAB_HEIGHT - 10)
            label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            self._tab_labels.append(label)

    def _select_tab(self, index: int) -> None:
        """Switch to a page by tab index."""
        self._pages.setCurrentIndex(index)

        # Visual feedback — highlight active tab
        for i, btn in enumerate(self._tab_buttons):
            opacity = "1.0" if i == index else "0.6"
            btn.setStyleSheet(f"background: transparent; opacity: {opacity};")

        log.info("Tab selected: %s", NAV_TABS[index]["key"])

    # ── Pages ───────────────────────────────────────────────────────

    def _setup_pages(self) -> None:
        """Create the QStackedWidget with all 3 pages."""
        from trcc_vision.adapters.gui.pages.page_hardware import PageHardware
        from trcc_vision.adapters.gui.pages.page_settings import PageSettings
        from trcc_vision.adapters.gui.pages.page_theme import PageTheme

        self._pages = QStackedWidget(self._root)
        self._pages.setGeometry(CONTENT_X, CONTENT_Y, CONTENT_WIDTH, CONTENT_HEIGHT)
        self._pages.setStyleSheet("background: transparent;")

        self._page_hardware = PageHardware(self._ctx)
        self._page_theme = PageTheme(self._ctx)
        self._page_settings = PageSettings(self._ctx)

        self._pages.addWidget(self._page_hardware)
        self._pages.addWidget(self._page_theme)
        self._pages.addWidget(self._page_settings)

    # ── Window dragging ─────────────────────────────────────────────

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Start drag if clicking on title bar area."""
        if (
            event.button() == Qt.MouseButton.LeftButton
            and event.position().y() < TITLEBAR_HEIGHT
        ):
            self._drag_pos = event.globalPosition().toPoint() - self.pos()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Drag window if title bar was clicked."""
        if self._drag_pos is not None:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """Stop dragging."""
        self._drag_pos = None
