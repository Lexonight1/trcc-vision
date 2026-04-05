"""Tests for the type-safe EventBus."""

from __future__ import annotations

from trcc_vision.core.events import (
    BrightnessChanged,
    DeviceDisconnected,
    Event,
    EventBus,
    SensorUpdated,
)


class TestEventBusSubscription:
    """Subscribe, publish, receive — the core pub/sub contract."""

    def test_subscriber_receives_published_event(
        self, event_bus: EventBus,
    ) -> None:
        received: list[Event] = []
        event_bus.subscribe(DeviceDisconnected, received.append)
        event_bus.publish(DeviceDisconnected())
        assert len(received) == 1
        assert isinstance(received[0], DeviceDisconnected)

    def test_multiple_subscribers_all_receive(
        self, event_bus: EventBus,
    ) -> None:
        a: list[Event] = []
        b: list[Event] = []
        event_bus.subscribe(BrightnessChanged, a.append)
        event_bus.subscribe(BrightnessChanged, b.append)
        event_bus.publish(BrightnessChanged(percent=75))
        assert len(a) == 1
        assert len(b) == 1

    def test_event_data_preserved(self, event_bus: EventBus) -> None:
        received: list[BrightnessChanged] = []
        event_bus.subscribe(BrightnessChanged, received.append)
        event_bus.publish(BrightnessChanged(percent=42))
        assert received[0].percent == 42


class TestEventBusIsolation:
    """Events only reach subscribers of the matching type."""

    def test_wrong_type_not_received(self, event_bus: EventBus) -> None:
        received: list[Event] = []
        event_bus.subscribe(SensorUpdated, received.append)
        event_bus.publish(DeviceDisconnected())
        assert len(received) == 0


class TestEventBusUnsubscribe:
    def test_unsubscribe_stops_delivery(self, event_bus: EventBus) -> None:
        received: list[Event] = []
        event_bus.subscribe(DeviceDisconnected, received.append)
        event_bus.unsubscribe(DeviceDisconnected, received.append)
        event_bus.publish(DeviceDisconnected())
        assert len(received) == 0

    def test_unsubscribe_missing_is_safe(self, event_bus: EventBus) -> None:
        event_bus.unsubscribe(DeviceDisconnected, lambda e: None)


class TestEventBusClear:
    def test_clear_removes_all(self, event_bus: EventBus) -> None:
        received: list[Event] = []
        event_bus.subscribe(DeviceDisconnected, received.append)
        event_bus.clear()
        event_bus.publish(DeviceDisconnected())
        assert len(received) == 0


class TestEventBusErrorHandling:
    def test_failing_handler_doesnt_block_others(
        self, event_bus: EventBus,
    ) -> None:
        received: list[Event] = []

        def bad_handler(event: Event) -> None:
            raise RuntimeError("boom")

        event_bus.subscribe(DeviceDisconnected, bad_handler)
        event_bus.subscribe(DeviceDisconnected, received.append)
        event_bus.publish(DeviceDisconnected())
        assert len(received) == 1
