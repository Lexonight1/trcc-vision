"""Fan use cases — monitor and control fan speeds."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trcc_vision.core.models import FanCurvePoint, FanState
    from trcc_vision.services.fan import FanService

log = logging.getLogger(__name__)


class GetFanStates:
    """Read all fan channel states."""

    def __init__(self, fan_service: FanService) -> None:
        self._svc = fan_service

    def execute(self) -> list[FanState]:
        log.debug("Reading fan states...")
        states = self._svc.get_states()
        log.info("Read %d fan channel(s)", len(states))
        return states


class SetFanDuty:
    """Set fan duty cycle for a channel."""

    def __init__(self, fan_service: FanService) -> None:
        self._svc = fan_service

    def execute(self, channel: int, duty_percent: int) -> bool:
        log.info("Setting fan channel %d to %d%%", channel, duty_percent)
        try:
            self._svc.set_duty(channel, duty_percent)
            return True
        except Exception:
            log.exception("Failed to set fan duty: channel=%d", channel)
            return False


class SetFanCurve:
    """Set temperature→duty curve for a channel."""

    def __init__(self, fan_service: FanService) -> None:
        self._svc = fan_service

    def execute(self, channel: int, points: list[FanCurvePoint]) -> bool:
        log.info("Setting fan curve: channel=%d, %d points", channel, len(points))
        try:
            self._svc.set_curve(channel, points)
            return True
        except Exception:
            log.exception("Failed to set fan curve: channel=%d", channel)
            return False
