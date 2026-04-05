"""Display service — high-level LCD display orchestration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from trcc_vision.core.models import DisplayState

if TYPE_CHECKING:
    from PIL import Image

    from trcc_vision.core.enums import DisplayMode, Rotation
    from trcc_vision.services.device import DeviceService
    from trcc_vision.services.media import MediaService
    from trcc_vision.services.theme import ThemeService

log = logging.getLogger(__name__)


class DisplayService:
    """Coordinates theme rendering, video playback, and LCD output."""

    def __init__(
        self,
        device_service: DeviceService,
        theme_service: ThemeService,
        media_service: MediaService,
    ) -> None:
        self._device = device_service
        self._theme = theme_service
        self._media = media_service
        self._state = DisplayState()

    @property
    def state(self) -> DisplayState:
        return self._state

    def set_mode(self, mode: DisplayMode) -> None:
        """Switch display mode (background/screencast/video)."""
        log.debug("set_mode() called: %s", mode.value)
        self._state.mode = mode
        log.info("Display mode → %s", mode.value)

    def set_rotation(self, rotation: Rotation) -> None:
        """Set LCD rotation."""
        log.debug("set_rotation() called: %d°", rotation.value)
        self._state.rotation = rotation
        log.info("Rotation → %d°", rotation.value)

    def set_brightness(self, percent: int) -> None:
        """Set LCD brightness (0-100)."""
        log.debug("set_brightness() called: %d%%", percent)
        self._state.brightness = max(0, min(100, percent))
        log.info("Brightness → %d%%", self._state.brightness)

    def send_image(self, img: Image.Image) -> None:
        """Resize, convert, and send a PIL image to the LCD."""
        log.debug("send_image() called: %dx%d", img.width, img.height)
        device = self._device.selected
        if not device:
            log.error("send_image() failed: no device selected")
            raise RuntimeError("No device selected")

        img.resize((device.lcd_width, device.lcd_height))
        # TODO: convert to RGB565 and send via device service
        log.info("Sent %dx%d image to LCD", device.lcd_width, device.lcd_height)
