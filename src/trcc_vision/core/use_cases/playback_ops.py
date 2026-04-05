"""Playback use cases — start/stop video and GIF playback."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from trcc_vision.core.events import PlaybackStateChanged

if TYPE_CHECKING:
    from pathlib import Path

    from trcc_vision.core.events import EventBus
    from trcc_vision.services.media import MediaService

log = logging.getLogger(__name__)


class StartPlayback:
    """Begin video/GIF playback on the LCD."""

    def __init__(self, media_service: MediaService, event_bus: EventBus) -> None:
        self._svc = media_service
        self._bus = event_bus

    def execute(self, path: Path, width: int, height: int) -> bool:
        log.info("Starting playback: %s → %dx%d", path.name, width, height)
        try:
            frames = self._svc.extract_frames(path, width, height)
            if not frames:
                log.warning("No frames extracted from %s", path.name)
                return False
            self._bus.publish(PlaybackStateChanged(
                is_playing=True, current_frame=0, total_frames=len(frames),
            ))
            log.info("Playback started: %d frames from %s", len(frames), path.name)
            return True
        except Exception:
            log.exception("Failed to start playback: %s", path.name)
            return False


class StopPlayback:
    """Stop current playback."""

    def __init__(self, event_bus: EventBus) -> None:
        self._bus = event_bus

    def execute(self) -> bool:
        log.info("Stopping playback")
        self._bus.publish(PlaybackStateChanged(is_playing=False))
        return True
