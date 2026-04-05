"""Domain enumerations — derived from WFanManager.Base.CMDType / DataType."""

from enum import Enum, IntEnum


class StrEnum(str, Enum):
    """str + Enum for Python 3.10 compatibility (StrEnum is 3.11+)."""


class SensorType(IntEnum):
    """Hardware sensor readings (maps to C# CMDType)."""

    CPU_TEMP = 0
    CPU_CORE_TEMP = 1
    CPU_PACKAGE_TEMP = 2
    CPU_VOLTAGE = 3
    CPU_POWER = 4
    CPU_LOAD = 5
    CPU_SPEED = 7
    RAM_USAGE_RATE = 6
    RAM_SIZE = 12
    GPU_TEMP = 13
    GPU_LOAD = 14
    GPU_SPEED = 15
    CPU_FAN_SPEED = 17
    CPU_NAME = 18
    GPU_NAME = 19
    GPU_POWER = 26
    RAM_USED = 28
    HDD_TEMP = 30
    HDD_CAPACITY = 31
    HDD_USED = 32
    HDD_AVAILABLE = 33
    HDD_USED_RATE = 34
    LAN_UPLOAD = 35
    LAN_DOWNLOAD = 36
    RAM_AVAILABLE = 37


class DisplayMode(StrEnum):
    """LCD display modes (maps to C# myUIMode)."""

    BACKGROUND = "background"     # Static image (myUIMode=1)
    SCREENCAST = "screencast"     # Live desktop capture (myUIMode=2)
    VIDEO = "video"               # Video/GIF playback (myUIMode=4)


class ThemeType(StrEnum):
    """Theme source categories."""

    DEFAULT = "default"
    USER = "user"
    CLOUD = "cloud"
    MASK = "mask"


class FanMode(StrEnum):
    """Fan control modes."""

    MANUAL = "manual"
    AUTO = "auto"
    CURVE = "curve"


class Rotation(IntEnum):
    """LCD rotation angles."""

    DEG_0 = 0
    DEG_90 = 90
    DEG_180 = 180
    DEG_270 = 270


class ConnectionType(StrEnum):
    """Device connection protocol."""

    ADB = "adb"
    TCP = "tcp"
    USB_HID = "usb_hid"


class ElementType(StrEnum):
    """Theme element types (maps to C# ControlType enum)."""

    DATA = "Data"       # Live sensor value display
    TIMER = "Timer"     # Clock/date display
    IMAGE = "Image"     # Static background image
    VIDEO = "Video"     # Animated video/GIF


class TimerFormat(IntEnum):
    """Timer display format (maps to C# TimerType)."""

    TIME = 0        # HH:MM:SS
    DATE = 1        # Date string
    WEEKDAY = 2     # Day of week


class FontType(StrEnum):
    """Font source type (typo 'Custome' matches C# source intentionally)."""

    DEFAULT = "Default"   # System font
    CUSTOM = "Custome"    # Custom font file bundled with app
