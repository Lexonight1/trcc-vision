# TR-VISION HOME — Claude Code Project Instructions

## Architecture — Hexagonal (Ports & Adapters)

### Layer Map
```
src/trcc_vision/
├── core/              # Domain: models, enums, ports (ABCs). ZERO external deps.
│   ├── models.py      # Pure dataclasses — DeviceInfo, SensorReading, ThemeConfig, etc.
│   ├── enums.py       # SensorType, DisplayMode, FanMode, Rotation, ConnectionType
│   └── ports.py       # ABC interfaces — DevicePort, SensorPort, FanPort, ConfigPort
├── services/          # Business logic. Depends on core only. No framework deps.
│   ├── device.py      # DeviceService — detect, select, send frames
│   ├── display.py     # DisplayService — LCD orchestration, mode switching
│   ├── fan.py         # FanService — fan monitoring, duty control, curves
│   ├── sensor.py      # SensorService — hardware sensor collection + cache
│   ├── theme.py       # ThemeService — theme CRUD, config parsing
│   └── media.py       # MediaService — video/GIF frame extraction
├── protocols/         # Hardware protocol implementations (ADB, TCP, HID)
├── infrastructure/    # Config persistence, logging, system sensor backends
├── adapters/
│   ├── cli/           # Typer CLI — thin wrapper calling services
│   ├── gui/           # PySide6 GUI — views, controllers
│   └── api/           # FastAPI REST — optional [api] extra
└── __version__.py
```

### Design Patterns
- **Dependency Injection**: Services receive ports in constructor, never import adapters
- **Repository Pattern**: ThemeRepositoryPort abstracts file/DB/remote storage
- **Abstract Base Classes**: Ports define contracts adapters must implement
- **Strategy Pattern**: Fan curves, display modes swappable at runtime
- **Observer Pattern**: Services broadcast state changes, adapters subscribe

## Source Material
- **Decompiled C# source**: `decompiled/WFanManager/` (125 files from WFanManager.exe)
- **Installed Windows app**: `TR-VISION HOME/` (DLLs, assets, configs)
- **Key namespaces**: WFanManager.Base (protocols), .Model (data), .ViewModel (logic), .View (WPF)
- **The C# is a reference for WHAT the hardware does, not HOW to write our code**

## Platform Support
- **Linux**: All non-EOL distros (Ubuntu 20.04+, Fedora, Debian, Arch, openSUSE, etc.)
- **macOS**: 10.15+
- **Windows**: 10+
- **BSD**: FreeBSD, OpenBSD, NetBSD
- Use `trcc_vision.infrastructure.platform` for OS detection and path resolution
- Never hardcode platform-specific paths — use `config_dir()`, `data_dir()`, `cache_dir()`, `log_dir()`
- Test platform-specific code with mocked `sys.platform`, not `sys.platform` checks in tests

## Conventions
- **Logging**: `log = logging.getLogger(__name__)` — never `print()` for diagnostics
- **Paths**: `pathlib.Path` everywhere, cross-platform via `infrastructure.platform`
- **Type hints**: On all public APIs
- **Tests**: `pytest` with `PYTHONPATH=src`
- **Linting**: `ruff check .` + `pyright` must pass before any commit
- **Python**: ≥3.10, use `from __future__ import annotations` for modern type syntax. No StrEnum (3.11+) — use `StrEnum(str, Enum)` backport in `core/enums.py`

## Development Workflow
- **Default branch**: `stable`
- **Never push without explicit user instruction**
- Commit freely during development, no version bump until release
- `ruff check .` + `pyright` before each commit

## Style
- KISS — minimal complexity, no over-engineering
- OOP — classes with clear single responsibilities
- DRY — extract helpers for repeated patterns, inline one-off logic
- Type hints on all public APIs
- NamedTuple/dataclass over raw tuples/dicts
