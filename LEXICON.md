# TR-VISION HOME — Lexicon

Shared terminology so everyone communicates using the same names.

## Hardware
| Term | Definition |
|------|-----------|
| **TR-VISION** | Thermalright's fan controller with LCD screen (the physical device) |
| **WFanManager** | Original Windows C# app name (decompiled source reference) |
| **LCD** | The small screen on the device (typically 480x480 or similar) |
| **Channel** | A single fan header on the controller (numbered 1-N) |
| **Duty** | Fan speed as percent (0-100%) of max RPM |
| **Fan Curve** | Temperature→duty mapping (list of points, linearly interpolated) |

## Protocols
| Term | Definition |
|------|-----------|
| **ADB** | Android Debug Bridge — used to push frames/commands to the device LCD |
| **TCP** | Network socket connection to device (alternative to ADB) |
| **HID** | USB Human Interface Device — potential control channel |
| **Frame** | A single LCD image (raw RGB or RGB565 bitmap) |

## Software Architecture
| Term | Definition |
|------|-----------|
| **Port** | Abstract interface (ABC) defining a contract at the hexagonal boundary |
| **Adapter** | Concrete implementation of a port (CLI, GUI, API, ADB, etc.) |
| **Service** | Core business logic class, depends only on ports, never on adapters |
| **Core** | The `core/` package — models, enums, ports. Zero external dependencies |
| **Protocol** | Hardware communication implementation in `protocols/` |

## Display
| Term | Definition |
|------|-----------|
| **Theme** | A directory containing background image, config, optional video/mask |
| **Overlay** | Sensor/time/date text elements rendered on top of the LCD image |
| **Element** | A single overlay item (time, date, CPU temp, custom text, etc.) |
| **Mask** | A transparent PNG layered on top of the background |
| **Screencast** | Live desktop region mirrored to the LCD |
| **Config DC** | Binary config file (`config1.dc`) storing overlay elements + display settings |

## Sensor Types (C# → Python mapping)
| C# Name | Python Enum | Meaning |
|---------|-------------|---------|
| CpuWenDu | CPU_TEMP | CPU temperature |
| CpuFuZai | CPU_LOAD | CPU load % |
| GpuWenDu | GPU_TEMP | GPU temperature |
| GpuFuZai | GPU_LOAD | GPU load % |
| CpuFszs | CPU_FAN_SPEED | CPU fan RPM |
| RamUsageRate | RAM_USAGE_RATE | RAM usage % |
| HddWenDu | HDD_TEMP | HDD/SSD temperature |
| LanUploadSpeed | LAN_UPLOAD | Network upload speed |
| LanDownloadSpeed | LAN_DOWNLOAD | Network download speed |

> **WenDu** = 温度 (temperature), **FuZai** = 负载 (load), **Fszs** = 风扇转速 (fan speed)
