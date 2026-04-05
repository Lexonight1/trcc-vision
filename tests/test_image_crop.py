"""Tests for the image crop tool — pure PIL, no Qt dependency."""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from trcc_vision.adapters.gui.widgets.image_crop_dialog import ImageCropper


@pytest.fixture()
def large_image() -> Image.Image:
    """1000x800 test image."""
    return Image.new("RGB", (1000, 800), color=(128, 64, 32))


@pytest.fixture()
def small_image() -> Image.Image:
    """200x200 test image."""
    return Image.new("RGB", (200, 200), color=(64, 128, 255))


@pytest.fixture()
def exact_image() -> Image.Image:
    """Exactly 480x480 test image."""
    return Image.new("RGB", (480, 480), color=(0, 255, 0))


class TestImageCropper:
    def test_crop_to_480x480(self, large_image: Image.Image, tmp_path: Path) -> None:
        cropper = ImageCropper(large_image)
        result_path = cropper.export(tmp_path)

        result = Image.open(result_path)
        assert result.size == (480, 480)

    def test_default_crop_is_centered(self, large_image: Image.Image) -> None:
        cropper = ImageCropper(large_image)
        left, top, right, bottom = cropper.crop_rect

        # 1000x800 image → crop centered at (260, 160)
        assert left == (1000 - 480) // 2
        assert top == (800 - 480) // 2
        assert right - left == 480
        assert bottom - top == 480

    def test_set_crop_position(self, large_image: Image.Image) -> None:
        cropper = ImageCropper(large_image)
        cropper.set_crop_position(100, 50)
        left, top, _, _ = cropper.crop_rect
        assert left == 100
        assert top == 50

    def test_crop_position_clamped(self, large_image: Image.Image) -> None:
        cropper = ImageCropper(large_image)
        # Try to set crop beyond image bounds
        cropper.set_crop_position(9999, 9999)
        left, top, right, bottom = cropper.crop_rect
        assert right <= large_image.width
        assert bottom <= large_image.height

    def test_rotate_cw(self, large_image: Image.Image, tmp_path: Path) -> None:
        cropper = ImageCropper(large_image)
        assert cropper.size == (1000, 800)

        cropper.rotate_cw()
        assert cropper.size == (800, 1000)  # dimensions swap

        result_path = cropper.export(tmp_path)
        result = Image.open(result_path)
        assert result.size == (480, 480)

    def test_rotate_ccw(self, large_image: Image.Image) -> None:
        cropper = ImageCropper(large_image)
        cropper.rotate_ccw()
        assert cropper.size == (800, 1000)

    def test_small_image_padded(self, small_image: Image.Image, tmp_path: Path) -> None:
        cropper = ImageCropper(small_image)
        result_path = cropper.export(tmp_path)

        result = Image.open(result_path)
        assert result.size == (480, 480)

        # Center pixel should be the original color (64, 128, 255)
        center = result.getpixel((240, 240))
        assert center == (64, 128, 255)

        # Corner should be black padding
        corner = result.getpixel((0, 0))
        assert corner == (0, 0, 0)

    def test_exact_size_no_change(self, exact_image: Image.Image, tmp_path: Path) -> None:
        cropper = ImageCropper(exact_image)
        result_path = cropper.export(tmp_path)

        result = Image.open(result_path)
        assert result.size == (480, 480)

    def test_reset_restores_original(self, large_image: Image.Image) -> None:
        cropper = ImageCropper(large_image)
        original_size = cropper.size

        cropper.rotate_cw()
        assert cropper.size != original_size

        cropper.reset()
        assert cropper.size == original_size

    def test_export_creates_png(self, large_image: Image.Image, tmp_path: Path) -> None:
        cropper = ImageCropper(large_image)
        result_path = cropper.export(tmp_path)

        assert result_path.exists()
        assert result_path.suffix == ".png"
