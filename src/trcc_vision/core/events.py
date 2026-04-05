"""Type-safe event bus — decouples services from adapters.

Unlike the C# MessageBus (string-keyed, untyped), events are dataclasses
dispatched by type. GUI subscribes for live updates; CLI/API ignore them.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

    from trcc_vision.core.models import DeviceInfo, SensorReading

log = logging.getLogger(__name__)


# ── Events ──────────────────────────────────────────────────────────────────


@dataclass
class Event:
    """Base class for all events."""


@dataclass
class SensorUpdated(Event):
    """Fired when sensor readings are refreshed."""

    readings: list[SensorReading]


@dataclass
class DeviceConnected(Event):
    """Fired when a device connection is established."""

    device: DeviceInfo


@dataclass
class DeviceDisconnected(Event):
    """Fired when the device is disconnected."""


@dataclass
class PlaybackStateChanged(Event):
    """Fired when playback starts, stops, or advances."""

    is_playing: bool
    current_frame: int = 0
    total_frames: int = 0


@dataclass
class BrightnessChanged(Event):
    """Fired when LCD brightness changes."""

    percent: int


@dataclass
class ThemeApplied(Event):
    """Fired when a theme is loaded and applied."""

    theme_name: str


# ── Bus ─────────────────────────────────────────────────────────────────────


class EventBus:
    """Publish/subscribe event bus with type-safe dispatch."""

    def __init__(self) -> None:
        self._subscribers: dict[type[Event], list[Callable]] = {}

    def subscribe(self, event_type: type[Event], callback: Callable) -> None:
        """Register a callback for an event type."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)
        log.debug("Subscribed %s to %s", callback.__qualname__, event_type.__name__)

    def unsubscribe(self, event_type: type[Event], callback: Callable) -> None:
        """Remove a callback for an event type."""
        if event_type in self._subscribers:
            try:
                self._subscribers[event_type].remove(callback)
                log.debug("Unsubscribed %s from %s", callback.__qualname__, event_type.__name__)
            except ValueError:
                log.warning(
                    "Cannot unsubscribe %s from %s: not found",
                    callback.__qualname__, event_type.__name__,
                )

    def publish(self, event: Event) -> None:
        """Dispatch an event to all subscribers of its type."""
        event_type = type(event)
        callbacks = self._subscribers.get(event_type, [])
        log.debug("Publishing %s to %d subscriber(s)", event_type.__name__, len(callbacks))
        for callback in callbacks:
            try:
                callback(event)
            except Exception:
                log.exception("Error in %s handler %s", event_type.__name__, callback.__qualname__)

    def clear(self) -> None:
        """Remove all subscriptions."""
        self._subscribers.clear()
        log.debug("All subscriptions cleared")
