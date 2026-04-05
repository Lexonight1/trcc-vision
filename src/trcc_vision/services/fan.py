"""Fan service — fan speed monitoring and control."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trcc_vision.core.enums import FanMode
    from trcc_vision.core.models import FanCurvePoint, FanState
    from trcc_vision.core.ports import FanPort

log = logging.getLogger(__name__)


class FanService:
    """Reads fan state and applies speed control (manual/auto/curve)."""

    def __init__(self, fan_port: FanPort) -> None:
        self._port = fan_port
        self._curves: dict[int, list[FanCurvePoint]] = {}

    def get_states(self) -> list[FanState]:
        """Read all fan channel states."""
        log.debug("get_states() called")
        states = self._port.get_fan_states()
        log.debug("get_states() returned %d channels", len(states))
        return states

    def set_mode(self, channel: int, mode: FanMode) -> None:
        """Set fan control mode for a channel."""
        log.debug("set_mode() called: channel=%d, mode=%s", channel, mode.value)
        log.info("Fan channel %d → %s mode", channel, mode.value)

    def set_duty(self, channel: int, duty_percent: int) -> None:
        """Manually set fan duty cycle (0-100)."""
        log.debug("set_duty() called: channel=%d, duty=%d", channel, duty_percent)
        duty_percent = max(0, min(100, duty_percent))
        self._port.set_fan_duty(channel, duty_percent)
        log.info("Fan channel %d duty → %d%%", channel, duty_percent)

    def set_curve(self, channel: int, points: list[FanCurvePoint]) -> None:
        """Set custom fan curve for a channel."""
        log.debug("set_curve() called: channel=%d, points=%d", channel, len(points))
        self._curves[channel] = sorted(points, key=lambda p: p.temp_c)
        log.info("Fan channel %d curve set (%d points)", channel, len(points))

    def apply_curve(self, channel: int, temp_c: float) -> int:
        """Evaluate fan curve at a given temperature, return duty percent."""
        log.debug("apply_curve() called: channel=%d, temp=%.1f°C", channel, temp_c)
        points = self._curves.get(channel, [])
        if not points:
            log.debug("No curve for channel %d, returning default 50%%", channel)
            return 50  # default fallback

        if temp_c <= points[0].temp_c:
            return points[0].duty_percent
        if temp_c >= points[-1].temp_c:
            return points[-1].duty_percent

        for i in range(len(points) - 1):
            lo, hi = points[i], points[i + 1]
            if lo.temp_c <= temp_c <= hi.temp_c:
                ratio = (temp_c - lo.temp_c) / (hi.temp_c - lo.temp_c)
                return int(lo.duty_percent + ratio * (hi.duty_percent - lo.duty_percent))

        return points[-1].duty_percent
