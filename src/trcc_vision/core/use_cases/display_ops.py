"""Display use cases — LCD image, color, brightness, rotation, mode."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from trcc_vision.core.events import BrightnessChanged

if TYPE_CHECKING:
    from pathlib import Path

    from PIL import Image

    from trcc_vision.core.enums import DisplayMode, Rotation
    from trcc_vision.core.events import EventBus
    from trcc_vision.services.display import DisplayService

log = logging.getLogger(__name__)


class SendImage:
    """Resize and send a PIL image to the LCD."""

    def __init__(self, display_service: DisplayService) -> None:
        self._svc = display_service

    def execute(self, img: Image.Image) -> bool:
        log.info("Sending image %dx%d to LCD", img.width, img.height)
        try:
            self._svc.send_image(img)
            return True
        except Exception:
            log.exception("Failed to send image")
            return False

    def execute_from_path(self, path: Path) -> bool:
        """Load image from file and send."""
        log.info("Sending image from %s", path)
        try:
            from PIL import Image as PILImage

            img = PILImage.open(path)
            return self.execute(img)
        except Exception:
            log.exception("Failed to load/send image from %s", path)
            return False


class SendColor:
    """Send a solid color to the LCD."""

    def __init__(self, display_service: DisplayService) -> None:
        self._svc = display_service

    def execute(self, r: int, g: int, b: int) -> bool:
        log.info("Sending color RGB(%d, %d, %d) to LCD", r, g, b)
        try:
            from PIL import Image as PILImage

            device = self._svc._device.selected
            if not device:
                log.error("No device selected")
                return False
            img = PILImage.new("RGB", (device.lcd_width, device.lcd_height), (r, g, b))
            self._svc.send_image(img)
            return True
        except Exception:
            log.exception("Failed to send color")
            return False


class SetBrightness:
    """Set LCD brightness (0-100)."""

    def __init__(self, display_service: DisplayService, event_bus: EventBus) -> None:
        self._svc = display_service
        self._bus = event_bus

    def execute(self, percent: int) -> bool:
        log.info("Setting brightness to %d%%", percent)
        try:
            self._svc.set_brightness(percent)
            self._bus.publish(BrightnessChanged(percent=self._svc.state.brightness))
            return True
        except Exception:
            log.exception("Failed to set brightness")
            return False


class SetRotation:
    """Set LCD rotation."""

    def __init__(self, display_service: DisplayService) -> None:
        self._svc = display_service

    def execute(self, rotation: Rotation) -> bool:
        log.info("Setting rotation to %d°", rotation.value)
        try:
            self._svc.set_rotation(rotation)
            return True
        except Exception:
            log.exception("Failed to set rotation")
            return False


class SetDisplayMode:
    """Switch display mode (background/screencast/video)."""

    def __init__(self, display_service: DisplayService) -> None:
        self._svc = display_service

    def execute(self, mode: DisplayMode) -> bool:
        log.info("Setting display mode to %s", mode.value)
        try:
            self._svc.set_mode(mode)
            return True
        except Exception:
            log.exception("Failed to set display mode")
            return False
