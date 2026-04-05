"""PySide6 GUI adapter — frameless image-based window.

Entry point for the GUI. Creates AppContext, builds MainWindow,
enters Qt event loop. All business logic goes through use cases.

Optional install: pip install trcc-vision[gui]
"""

from __future__ import annotations

import logging
import sys

log = logging.getLogger(__name__)


def run(mock: bool = False) -> None:
    """Launch the TR-VISION HOME GUI."""
    from trcc_vision.infrastructure.i18n import setup_i18n
    from trcc_vision.infrastructure.logging import setup_logging

    setup_logging(console_level=logging.INFO)
    setup_i18n()
    log.info("Starting TR-VISION HOME GUI (mock=%s)", mock)

    from PySide6.QtWidgets import QApplication

    from trcc_vision.adapters.gui.main_window import MainWindow
    from trcc_vision.core.context import AppContext

    qt_app = QApplication(sys.argv)
    ctx = AppContext(mock=mock)
    window = MainWindow(ctx)
    window.show()

    log.info("Entering Qt event loop")
    sys.exit(qt_app.exec())


if __name__ == "__main__":
    run()
