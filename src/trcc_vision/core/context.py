"""AppContext — dependency injection container.

Creates one instance per app lifecycle. All adapters (CLI, GUI, API) use
the same context to access use cases, ensuring identical behavior.

Pass mock=True to wire fake device/fan ports for development without hardware.
"""

from __future__ import annotations

import logging

from trcc_vision.core.events import EventBus
from trcc_vision.core.use_cases.device_ops import (
    ConnectDevice,
    DetectDevices,
    DisconnectDevice,
    GetDeviceStatus,
)
from trcc_vision.core.use_cases.display_ops import (
    SendColor,
    SendImage,
    SetBrightness,
    SetDisplayMode,
    SetRotation,
)
from trcc_vision.core.use_cases.fan_ops import GetFanStates, SetFanCurve, SetFanDuty
from trcc_vision.core.use_cases.playback_ops import StartPlayback, StopPlayback
from trcc_vision.core.use_cases.sensor_ops import ReadAllSensors, ReadSensor
from trcc_vision.core.use_cases.system_ops import GetSystemInfo, RunDoctor
from trcc_vision.core.use_cases.theme_ops import (
    DeleteTheme,
    ListThemes,
    LoadTheme,
    SaveTheme,
)
from trcc_vision.services.device import DeviceService
from trcc_vision.services.display import DisplayService
from trcc_vision.services.fan import FanService
from trcc_vision.services.media import MediaService
from trcc_vision.services.sensor import SensorService

log = logging.getLogger(__name__)


class AppContext:
    """Wires services, ports, and use cases. One instance per app lifecycle.

    Args:
        mock: If True, wire fake device/fan ports for development.

    Usage:
        ctx = AppContext(mock=True)
        devices = ctx.detect_devices.execute()
    """

    def __init__(self, mock: bool = False) -> None:
        log.info("Initializing AppContext (mock=%s)...", mock)

        self.mock = mock
        self.event_bus = EventBus()

        # ── Sensor (always real, platform-specific) ─────────────────
        from trcc_vision.infrastructure.sensors import create_sensor_port

        self.sensor_service = SensorService(create_sensor_port())

        # ── Media (no port, uses ffmpeg/Pillow directly) ────────────
        self.media_service = MediaService()

        # ── Config persistence ──────────────────────────────────────
        from trcc_vision.infrastructure.config import JsonConfig
        self.config = JsonConfig()

        # ── Theme repository (always available — bundled + user) ────
        from trcc_vision.adapters.gui.constants import THEME_ASSETS
        from trcc_vision.infrastructure.platform import data_dir
        from trcc_vision.infrastructure.theme_repository import FileThemeRepository
        from trcc_vision.services.theme import ThemeService

        theme_repo = FileThemeRepository(THEME_ASSETS, data_dir() / "themes")
        self.theme_service: ThemeService | None = ThemeService(theme_repo)

        # ── Device + Display + Fan ──────────────────────────────────
        if mock:
            self._init_mock()
        else:
            self._init_real()

        # ── Use cases (always wired) ────────────────────────────────
        self.read_all_sensors = ReadAllSensors(self.sensor_service, self.event_bus)
        self.read_sensor = ReadSensor(self.sensor_service)
        self.get_system_info = GetSystemInfo()
        self.run_doctor = RunDoctor()
        self.start_playback = StartPlayback(self.media_service, self.event_bus)
        self.stop_playback = StopPlayback(self.event_bus)

        self._wire_device_use_cases()
        self._wire_display_use_cases()
        self._wire_fan_use_cases()
        self._wire_theme_use_cases()

        log.info("AppContext initialized (mock=%s)", mock)

    def _init_mock(self) -> None:
        """Wire mock ports for development without hardware."""
        from trcc_vision.infrastructure.mock_device import MockDevicePort
        from trcc_vision.infrastructure.mock_fan import MockFanPort

        log.info("Mock mode: wiring fake device + fan ports")
        device_port = MockDevicePort()
        fan_port = MockFanPort()

        self.device_service: DeviceService | None = DeviceService(device_port)
        self.display_service: DisplayService | None = DisplayService(
            self.device_service,
            self.theme_service,  # type: ignore[arg-type]  # always set above
            self.media_service,
        )
        self.fan_service: FanService | None = FanService(fan_port)

        # Auto-connect the mock device so all use cases work immediately
        from trcc_vision.infrastructure.mock_device import MOCK_DEVICE
        self.device_service.select(MOCK_DEVICE)
        log.info("Mock device auto-connected: %s", MOCK_DEVICE.name)

    def _init_real(self) -> None:
        """Wire real ports via platform-specific ADB factory."""
        from trcc_vision.protocols.adb_factory import create_adb_port
        from trcc_vision.protocols.device_protocol import DeviceProtocol

        adb_port = create_adb_port()
        device_port = DeviceProtocol(adb=adb_port)

        self.device_service: DeviceService | None = DeviceService(device_port, adb=adb_port)  # type: ignore[no-redef]
        self.display_service: DisplayService | None = DisplayService(  # type: ignore[no-redef]
            self.device_service,
            self.theme_service,  # type: ignore[arg-type]
            self.media_service,
        )
        self.fan_service: FanService | None = None  # type: ignore[no-redef]  # TODO: wire FanPort

    def _wire_device_use_cases(self) -> None:
        if self.device_service:
            self.detect_devices: DetectDevices | None = DetectDevices(self.device_service)
            self.connect_device: ConnectDevice | None = ConnectDevice(
                self.device_service, self.event_bus,
            )
            self.disconnect_device: DisconnectDevice | None = DisconnectDevice(
                self.device_service, self.event_bus,
            )
            self.get_device_status: GetDeviceStatus | None = GetDeviceStatus(self.device_service)
        else:
            self.detect_devices = None
            self.connect_device = None
            self.disconnect_device = None
            self.get_device_status = None
            log.debug("Device use cases not available (no DevicePort)")

    def _wire_display_use_cases(self) -> None:
        if self.display_service:
            self.send_image: SendImage | None = SendImage(self.display_service)
            self.send_color: SendColor | None = SendColor(self.display_service)
            self.set_brightness: SetBrightness | None = SetBrightness(
                self.display_service, self.event_bus,
            )
            self.set_rotation: SetRotation | None = SetRotation(self.display_service)
            self.set_display_mode: SetDisplayMode | None = SetDisplayMode(self.display_service)
        else:
            self.send_image = None
            self.send_color = None
            self.set_brightness = None
            self.set_rotation = None
            self.set_display_mode = None
            log.debug("Display use cases not available (no DevicePort)")

    def _wire_fan_use_cases(self) -> None:
        if self.fan_service:
            self.get_fan_states: GetFanStates | None = GetFanStates(self.fan_service)
            self.set_fan_duty: SetFanDuty | None = SetFanDuty(self.fan_service)
            self.set_fan_curve: SetFanCurve | None = SetFanCurve(self.fan_service)
        else:
            self.get_fan_states = None
            self.set_fan_duty = None
            self.set_fan_curve = None
            log.debug("Fan use cases not available (no FanPort)")

    def _wire_theme_use_cases(self) -> None:
        if self.theme_service:
            self.list_themes: ListThemes | None = ListThemes(self.theme_service)
            self.load_theme: LoadTheme | None = LoadTheme(self.theme_service, self.event_bus)
            self.save_theme: SaveTheme | None = SaveTheme(self.theme_service)
            self.delete_theme: DeleteTheme | None = DeleteTheme(self.theme_service)
        else:
            self.list_themes = None
            self.load_theme = None
            self.save_theme = None
            self.delete_theme = None
            log.debug("Theme use cases not available (no ThemeRepositoryPort)")
