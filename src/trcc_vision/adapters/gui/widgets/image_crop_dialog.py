"""Image crop dialog — import, crop, and rotate images for theme backgrounds.

Uses Pillow (already a dependency) for all image operations.
Output is always a 480x480 PNG suitable for theme backgrounds.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING

from PIL import Image

from trcc_vision.adapters.gui.constants import LCD_HEIGHT, LCD_WIDTH

if TYPE_CHECKING:
    from pathlib import Path

log = logging.getLogger(__name__)

# Maximum preview size in the dialog
_PREVIEW_MAX = 600


class ImageCropper:
    """Pure-logic image cropper — no Qt dependency, fully testable.

    Holds a PIL Image and provides crop/rotate/export operations.
    The crop region is a 480x480 rect that the caller can reposition.
    """

    def __init__(self, image: Image.Image) -> None:
        self._original = image.convert("RGBA")
        self._image = self._original.copy()
        # Default crop: centered 480x480
        self._crop_x = max(0, (self._image.width - LCD_WIDTH) // 2)
        self._crop_y = max(0, (self._image.height - LCD_HEIGHT) // 2)

    @property
    def image(self) -> Image.Image:
        return self._image

    @property
    def size(self) -> tuple[int, int]:
        return self._image.size

    @property
    def crop_rect(self) -> tuple[int, int, int, int]:
        """(left, top, right, bottom) of the crop region."""
        return (
            self._crop_x, self._crop_y,
            self._crop_x + LCD_WIDTH, self._crop_y + LCD_HEIGHT,
        )

    def set_crop_position(self, x: int, y: int) -> None:
        """Move the crop rect, clamping to image bounds."""
        self._crop_x = max(0, min(x, self._image.width - LCD_WIDTH))
        self._crop_y = max(0, min(y, self._image.height - LCD_HEIGHT))

    def rotate_cw(self) -> None:
        """Rotate 90° clockwise."""
        self._image = self._image.rotate(-90, expand=True)
        self._clamp_crop()
        log.debug("Rotated CW → %dx%d", *self._image.size)

    def rotate_ccw(self) -> None:
        """Rotate 90° counter-clockwise."""
        self._image = self._image.rotate(90, expand=True)
        self._clamp_crop()
        log.debug("Rotated CCW → %dx%d", *self._image.size)

    def reset(self) -> None:
        """Reset to original image."""
        self._image = self._original.copy()
        self._clamp_crop()
        log.debug("Image reset to original %dx%d", *self._image.size)

    def export(self, output_dir: Path) -> Path:
        """Crop to 480x480 and save as PNG. Returns the output path."""
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")[:17]
        output_path = output_dir / f"{timestamp}.png"

        cropped = self._cropped_image()
        cropped.save(output_path, "PNG")
        log.info("Exported cropped image: %s (%dx%d)", output_path, LCD_WIDTH, LCD_HEIGHT)
        return output_path

    def _cropped_image(self) -> Image.Image:
        """Get the 480x480 cropped result."""
        w, h = self._image.size

        if w < LCD_WIDTH or h < LCD_HEIGHT:
            # Image smaller than 480x480 — paste centered on black background
            result = Image.new("RGBA", (LCD_WIDTH, LCD_HEIGHT), (0, 0, 0, 255))
            paste_x = (LCD_WIDTH - w) // 2
            paste_y = (LCD_HEIGHT - h) // 2
            result.paste(self._image, (paste_x, paste_y))
            return result.convert("RGB")

        left, top, right, bottom = self.crop_rect
        return self._image.crop((left, top, right, bottom)).convert("RGB")

    def _clamp_crop(self) -> None:
        """Ensure crop rect stays within image bounds after rotation/reset."""
        w, h = self._image.size
        self._crop_x = max(0, min(self._crop_x, w - LCD_WIDTH))
        self._crop_y = max(0, min(self._crop_y, h - LCD_HEIGHT))
        # If image is smaller than LCD, center
        if w < LCD_WIDTH:
            self._crop_x = 0
        if h < LCD_HEIGHT:
            self._crop_y = 0
