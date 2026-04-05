"""Media service — video/GIF frame extraction for LCD playback."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from trcc_vision.core.models import PlayFile

if TYPE_CHECKING:
    from pathlib import Path

log = logging.getLogger(__name__)


class MediaService:
    """Extracts frames from video/GIF files for LCD playback."""

    def probe(self, path: Path) -> PlayFile:
        """Probe a media file for metadata (duration, frame count, resolution)."""
        log.debug("probe() called: %s", path)
        # TODO: implement via ffprobe
        log.info("Probed media file: %s", path.name)
        return PlayFile(
            path=path,
            name=path.stem,
        )

    def extract_frames(
        self,
        path: Path,
        width: int,
        height: int,
    ) -> list[bytes]:
        """Extract all frames as raw RGB data, resized to LCD dimensions."""
        log.debug("extract_frames() called: %s → %dx%d", path, width, height)
        # TODO: implement via ffmpeg subprocess or Pillow for GIFs
        frames: list[bytes] = []
        log.info("Extracted %d frames from %s → %dx%d", len(frames), path.name, width, height)
        return frames
