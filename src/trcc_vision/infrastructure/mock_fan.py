"""Mock fan port — simulates fan channels for development without hardware.

Implements FanPort with:
- Configurable number of channels (default 4)
- Randomized RPM readings with realistic drift
- Duty cycle tracking

Activate via: trcc-vision --mock fans
"""

from __future__ import annotations

import logging
import random

from trcc_vision.core.enums import FanMode
from trcc_vision.core.models import FanState
from trcc_vision.core.ports import FanPort

log = logging.getLogger(__name__)


class MockFanPort(FanPort):
    """Fake FanPort that simulates fan channels in memory."""

    def __init__(self, num_channels: int = 4) -> None:
        self._num_channels = num_channels
        self._duties: dict[int, int] = {ch: 50 for ch in range(num_channels)}
        self._base_rpms: dict[int, int] = {
            ch: random.randint(900, 1300) for ch in range(num_channels)  # noqa: S311
        }
        log.info("MockFanPort created: %d channels", num_channels)

    def get_fan_states(self) -> list[FanState]:
        """Return simulated fan states with slight RPM drift."""
        states: list[FanState] = []
        for ch in range(self._num_channels):
            duty = self._duties[ch]
            # Scale RPM by duty: at 100% duty → full base RPM, at 0% → ~200 RPM idle
            base = self._base_rpms[ch]
            rpm = int(200 + (base - 200) * duty / 100)
            # Add ±30 RPM drift for realism
            rpm += random.randint(-30, 30)  # noqa: S311
            rpm = max(0, rpm)

            states.append(FanState(
                channel=ch,
                rpm=rpm,
                duty_percent=duty,
                mode=FanMode.MANUAL if duty != 50 else FanMode.AUTO,
            ))

        log.debug("Mock fan states: %s", [(s.channel, s.rpm, s.duty_percent) for s in states])
        return states

    def set_fan_duty(self, channel: int, duty_percent: int) -> None:
        """Record a duty cycle change."""
        if channel < 0 or channel >= self._num_channels:
            raise ValueError(f"Invalid channel {channel}, max is {self._num_channels - 1}")
        duty_percent = max(0, min(100, duty_percent))
        self._duties[channel] = duty_percent
        log.info("Mock fan channel %d duty → %d%%", channel, duty_percent)
