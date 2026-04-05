"""Tests for centralized logging setup."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from trcc_vision.infrastructure.logging import (
    LOG_FILE_NAME,
    reset_logging,
    setup_logging,
)

if TYPE_CHECKING:
    from pathlib import Path


class TestSetupLogging:
    def teardown_method(self) -> None:
        reset_logging()

    def test_console_handler_added(self) -> None:
        setup_logging(enable_file=False)
        root = logging.getLogger()
        stream_handlers = [h for h in root.handlers if isinstance(h, logging.StreamHandler)]
        assert len(stream_handlers) >= 1

    def test_file_handler_created(self, tmp_path: Path) -> None:
        log_file = tmp_path / "test.log"
        setup_logging(log_file=log_file, enable_console=False)
        root = logging.getLogger()
        from logging.handlers import RotatingFileHandler
        file_handlers = [h for h in root.handlers if isinstance(h, RotatingFileHandler)]
        assert len(file_handlers) == 1
        assert log_file.exists()

    def test_log_file_default_name(self, tmp_path: Path) -> None:
        log_file = tmp_path / LOG_FILE_NAME
        setup_logging(log_file=log_file, enable_console=False)
        # Write a log message to flush
        logging.getLogger("test").info("hello")
        assert log_file.exists()
        content = log_file.read_text()
        assert "hello" in content

    def test_verbose_level(self) -> None:
        setup_logging(console_level=logging.DEBUG, enable_file=False)
        root = logging.getLogger()
        # Filter out pytest's LogCaptureHandler — only check our StreamHandlers
        our_handlers = [
            h for h in root.handlers
            if isinstance(h, logging.StreamHandler) and type(h) is logging.StreamHandler
        ]
        assert len(our_handlers) == 1
        assert our_handlers[0].level == logging.DEBUG

    def test_quiet_level(self) -> None:
        setup_logging(console_level=logging.WARNING, enable_file=False)
        root = logging.getLogger()
        our_handlers = [
            h for h in root.handlers
            if isinstance(h, logging.StreamHandler) and type(h) is logging.StreamHandler
        ]
        assert len(our_handlers) == 1
        assert our_handlers[0].level == logging.WARNING

    def test_idempotent(self) -> None:
        setup_logging(enable_file=False)
        handler_count = len(logging.getLogger().handlers)
        setup_logging(enable_file=False)  # second call should be no-op
        assert len(logging.getLogger().handlers) == handler_count

    def test_creates_log_directory(self, tmp_path: Path) -> None:
        log_file = tmp_path / "subdir" / "deep" / "test.log"
        setup_logging(log_file=log_file, enable_console=False)
        assert log_file.parent.exists()


class TestResetLogging:
    def test_clears_handlers(self) -> None:
        setup_logging(enable_file=False)
        assert len(logging.getLogger().handlers) > 0
        reset_logging()
        assert len(logging.getLogger().handlers) == 0

    def test_allows_reinit(self) -> None:
        setup_logging(enable_file=False)
        reset_logging()
        setup_logging(enable_file=False)
        assert len(logging.getLogger().handlers) > 0
