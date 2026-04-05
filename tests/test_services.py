"""Tests for the service layer — business logic with injected stub ports."""

from __future__ import annotations

from trcc_vision.core.enums import SensorType
from trcc_vision.core.models import FanCurvePoint
from trcc_vision.services.fan import FanService
from trcc_vision.services.sensor import SensorService

from .conftest import StubFanPort


class TestSensorService:
    """SensorService: read, cache, and retrieve hardware readings."""

    def test_read_all_returns_readings(
        self, sensor_service: SensorService,
    ) -> None:
        result = sensor_service.read_all()
        assert len(result) == 4

    def test_get_cached_after_read_all(
        self, sensor_service: SensorService,
    ) -> None:
        sensor_service.read_all()
        cpu = sensor_service.get(SensorType.CPU_TEMP)
        assert cpu is not None
        assert cpu.value == 55.0
        assert cpu.label == "CPU Package"

    def test_get_returns_none_for_missing(
        self, sensor_service: SensorService,
    ) -> None:
        assert sensor_service.get(SensorType.HDD_TEMP) is None

    def test_clear_cache_forces_fresh_read(
        self, sensor_service: SensorService,
    ) -> None:
        sensor_service.read_all()
        sensor_service.clear_cache()
        # After clear, get() goes back to port (which still has data)
        cpu = sensor_service.get(SensorType.CPU_TEMP)
        assert cpu is not None


class TestFanService:
    """FanService: duty control and curve interpolation."""

    def test_set_duty_records_on_port(
        self, fan_service: FanService, fan_port: StubFanPort,
    ) -> None:
        fan_service.set_duty(0, 75)
        assert fan_port.duties[0] == 75

    def test_set_duty_clamps_to_100(
        self, fan_service: FanService, fan_port: StubFanPort,
    ) -> None:
        fan_service.set_duty(0, 150)
        assert fan_port.duties[0] == 100

    def test_curve_interpolation(self, fan_service: FanService) -> None:
        fan_service.set_curve(0, [
            FanCurvePoint(temp_c=30, duty_percent=20),
            FanCurvePoint(temp_c=50, duty_percent=60),
            FanCurvePoint(temp_c=80, duty_percent=100),
        ])
        assert fan_service.apply_curve(0, 30) == 20   # exact low point
        assert fan_service.apply_curve(0, 40) == 40   # midpoint interpolation
        assert fan_service.apply_curve(0, 80) == 100  # exact high point
        assert fan_service.apply_curve(0, 10) == 20   # below min → clamp
        assert fan_service.apply_curve(0, 90) == 100  # above max → clamp

    def test_no_curve_returns_default(self, fan_service: FanService) -> None:
        assert fan_service.apply_curve(0, 50) == 50

    def test_get_states_empty(self, fan_service: FanService) -> None:
        assert fan_service.get_states() == []

    def test_get_states_after_set(
        self, fan_service: FanService, fan_port: StubFanPort,
    ) -> None:
        fan_service.set_duty(0, 60)
        fan_service.set_duty(1, 80)
        states = fan_service.get_states()
        assert len(states) == 2
        assert states[0].duty_percent == 60
        assert states[1].duty_percent == 80
