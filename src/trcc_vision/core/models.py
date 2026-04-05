"""Domain models — pure dataclasses with boundary validation via __post_init__.

Validation runs when data enters the core (from adapters, protocols, config files).
Internal service-to-service calls trust the data is already valid.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from trcc_vision.core.enums import (
    ConnectionType,
    DisplayMode,
    ElementType,
    FanMode,
    FontType,
    Rotation,
    SensorType,
    ThemeType,
    TimerFormat,
)

_HEX_COLOR_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")

if TYPE_CHECKING:
    from pathlib import Path


def _clamp(value: int, lo: int, hi: int, name: str) -> int:
    """Clamp an integer to [lo, hi], raise if not an int."""
    if not isinstance(value, int):
        raise TypeError(f"{name} must be int, got {type(value).__name__}")
    return max(lo, min(hi, value))


@dataclass(frozen=True)
class DeviceInfo:
    """Discovered TR-VISION device."""

    name: str
    connection: ConnectionType
    address: str  # ADB serial, IP:port, or USB path
    lcd_width: int = 480
    lcd_height: int = 480

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("DeviceInfo.name cannot be empty")
        if not self.address:
            raise ValueError("DeviceInfo.address cannot be empty")
        if self.lcd_width <= 0 or self.lcd_height <= 0:
            raise ValueError(
                f"LCD dimensions must be positive, got {self.lcd_width}x{self.lcd_height}"
            )


@dataclass
class SensorReading:
    """Single hardware sensor value."""

    sensor_type: SensorType
    label: str
    value: float
    unit: str
    timestamp: float = 0.0


@dataclass
class FanState:
    """Fan channel state."""

    channel: int
    rpm: int = 0
    duty_percent: int = 0
    mode: FanMode = FanMode.AUTO

    def __post_init__(self) -> None:
        if self.channel < 0:
            raise ValueError(f"Fan channel must be >= 0, got {self.channel}")
        if self.rpm < 0:
            raise ValueError(f"Fan RPM must be >= 0, got {self.rpm}")
        self.duty_percent = _clamp(self.duty_percent, 0, 100, "duty_percent")


@dataclass
class FanCurvePoint:
    """Single point on a fan curve."""

    temp_c: int
    duty_percent: int

    def __post_init__(self) -> None:
        self.duty_percent = _clamp(self.duty_percent, 0, 100, "duty_percent")


@dataclass
class DataItem:
    """Sensor binding — which hardware sensor an element displays."""

    data_num: int = 0   # SensorType ID (0=CPU temp, 5=CPU load, 7=CPU speed, etc.)
    name: str = ""      # Display label ("CPU温度", "CPU使用率")


@dataclass
class ThemeElement:
    """Single element in a theme layout (Data, Timer, Image, or Video).

    Full schema derived from all 10 default Theme*.xml files and the
    decompiled C# ThemeElement class.
    """

    element_type: ElementType
    content: str = ""

    # Sensor binding (DATA elements)
    data_item: DataItem = field(default_factory=DataItem)
    data_unit: str = ""
    show_data_type_name: bool = False

    # Timer (TIMER elements)
    timer_type: TimerFormat = TimerFormat.TIME

    # Media (IMAGE / VIDEO elements)
    image_file_path: str = ""
    video_file: str = ""
    play_count: int = 0

    # Position & size — floats, not ints (XML has decimal precision)
    x: float = 0.0
    y: float = 0.0
    width: int = 0      # 0 = auto-size
    height: int = 0     # 0 = auto-size
    scale_x: float = 1.0
    scale_y: float = 1.0
    z_index: int = 0    # can be negative (video = -1)

    # Font
    font_family: str = "NI7SEG"
    font_size: float = 20.0
    font_type: FontType = FontType.DEFAULT
    font_file_name: str = ""
    font_weight: bool = False    # bold
    font_style: bool = False     # italic

    # Color & opacity
    color: str = "#FFFFFF"       # hex #RRGGBB (matches XML ColorString)
    opacity: float = 1.0         # 0.0–1.0

    # UI metadata
    uc_name: str = ""
    marquee_type: int = 0        # 0 = no scrolling

    def __post_init__(self) -> None:
        if self.font_size <= 0:
            raise ValueError(f"font_size must be positive, got {self.font_size}")
        if self.play_count < 0:
            raise ValueError(f"play_count must be >= 0, got {self.play_count}")
        self.opacity = max(0.0, min(1.0, self.opacity))
        if self.color and not _HEX_COLOR_RE.match(self.color):
            raise ValueError(f"color must be #RRGGBB hex, got '{self.color}'")


@dataclass
class ThemeConfig:
    """Full theme layout — parsed from Theme*.xml files."""

    name: str = ""
    theme_type: str = "DefaultTheme"  # "DefaultTheme" or "CustomTheme"
    rotation: int = 0
    elements: list[ThemeElement] = field(default_factory=list)
    display_data: bool = True
    display_timer: bool = True
    display_image: bool = True
    display_video: bool = False
    display_text_block: bool = False


@dataclass
class ThemeInfo:
    """Theme metadata."""

    name: str
    path: Path
    theme_type: ThemeType = ThemeType.USER
    has_background: bool = True
    has_video: bool = False
    has_mask: bool = False
    preview_path: Path | None = None

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("ThemeInfo.name cannot be empty")


@dataclass
class DisplayState:
    """Current LCD display state."""

    mode: DisplayMode = DisplayMode.BACKGROUND
    rotation: Rotation = Rotation.DEG_0
    brightness: int = 100
    theme: ThemeInfo | None = None
    config: ThemeConfig | None = None
    is_playing: bool = False
    current_frame: int = 0
    total_frames: int = 0

    def __post_init__(self) -> None:
        self.brightness = _clamp(self.brightness, 0, 100, "brightness")
        if self.current_frame < 0:
            raise ValueError(f"current_frame must be >= 0, got {self.current_frame}")
        if self.total_frames < 0:
            raise ValueError(f"total_frames must be >= 0, got {self.total_frames}")


@dataclass
class PlayFile:
    """Media file for LCD playback (maps to C# PlayFile)."""

    path: Path
    name: str
    duration_ms: int = 0
    frame_count: int = 0
    width: int = 0
    height: int = 0

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("PlayFile.name cannot be empty")
        if self.duration_ms < 0:
            raise ValueError(f"duration_ms must be >= 0, got {self.duration_ms}")
        if self.frame_count < 0:
            raise ValueError(f"frame_count must be >= 0, got {self.frame_count}")
