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
        self._state.mode = mode
        log.info("Display mode → %s", mode.value)

    def set_rotation(self, rotation: Rotation) -> None:
        """Set LCD rotation and send command to device."""
        from trcc_vision.protocols.commands import rotation as rotation_cmd

        self._state.rotation = rotation
        if self._device.is_connected:
            msg = rotation_cmd(rotation.value)
            self._device.send_command(msg.serialize())
            log.info("Rotation → %d°", rotation.value)
        else:
            log.warning("Rotation → %d° (not sent — device not connected)", rotation.value)

    def set_brightness(self, percent: int) -> None:
        """Set LCD brightness (0-100) and send command to device."""
        from trcc_vision.protocols.commands import brightness

        self._state.brightness = max(0, min(100, percent))
        if self._device.is_connected:
            msg = brightness(self._state.brightness)
            self._device.send_command(msg.serialize())
            log.info("Brightness → %d%%", self._state.brightness)
        else:
            log.warning(
                "Brightness → %d%% (not sent — device not connected)",
                self._state.brightness,
            )

    def screen_power(self, on: bool) -> None:
        """Turn LCD screen on or off."""
        from trcc_vision.protocols.commands import screen_power

        label = "ON" if on else "OFF"
        if self._device.is_connected:
            msg = screen_power(on)
            self._device.send_command(msg.serialize())
            log.info("Screen → %s", label)
        else:
            log.warning("Screen → %s (not sent — device not connected)", label)

    def send_image(self, img: Image.Image) -> None:
        """Resize, convert to RGB565, and send a PIL image to the LCD."""
        device = self._device.selected
        if not device:
            raise RuntimeError("No device selected")

        # Resize to LCD dimensions
        resized = img.resize((device.lcd_width, device.lcd_height))

        # Convert to RGB565
        try:
            from trcc_vision.protocols.commands import image_to_rgb565_numpy
            rgb565 = image_to_rgb565_numpy(resized)
        except ImportError:
            from trcc_vision.protocols.commands import image_to_rgb565
            rgb565 = image_to_rgb565(resized)

        # Send frame to device
        self._device.send_frame(rgb565, device.lcd_width, device.lcd_height)
        log.info(
            "Sent %dx%d image to LCD (%d bytes)",
            device.lcd_width, device.lcd_height, len(rgb565),
        )

    def push_sensor_data(
        self,
        *,
        cpu_temp: int = 0,
        cpu_usage: int = 0,
        cpu_speed_mhz: int = 0,
        memory_usage: int = 0,
        gpu_temp: int = 0,
        gpu_load: int = 0,
        fan_rpm: int = 0,
    ) -> None:
        """Push live sensor data to the device LCD overlay."""
        from trcc_vision.protocols.commands import sensor_data

        if not self._device.is_connected:
            log.debug("Sensor push skipped — device not connected")
            return

        msg = sensor_data(
            cpu_core_temp=cpu_temp,
            cpu_usage=cpu_usage,
            cpu_speed_mhz=cpu_speed_mhz,
            memory_usage=memory_usage,
            gpu_temp=gpu_temp,
            gpu_load=gpu_load,
            fan_rpm=fan_rpm,
        )
        self._device.send_command(msg.serialize())
        log.debug("Pushed sensor data to device")
