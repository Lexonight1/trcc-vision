# TR-VISION HOME — Claude Code Project Instructions

## Architecture — Hexagonal (Ports & Adapters)

### Layer Map
```
src/trcc_vision/
├── core/              # Domain: models, enums, ports (ABCs). ZERO external deps.
│   ├── models.py      # Pure dataclasses — DeviceInfo, SensorReading, ThemeConfig, etc.
│   ├── enums.py       # SensorType, DisplayMode, FanMode, Rotation, ConnectionType
│   ├── ports.py       # ABC interfaces — DevicePort, SensorPort, FanPort, ConfigPort
│   ├── events.py      # EventBus + typed event dataclasses (SensorUpdated, ThemeApplied, etc.)
│   ├── context.py     # AppContext — DI container wiring all services + use cases
│   └── use_cases/     # Command handlers — ListThemes, LoadTheme, SaveTheme, etc.
├── services/          # Business logic. Depends on core only. No framework deps.
│   ├── device.py      # DeviceService — detect, select, send frames
│   ├── display.py     # DisplayService — LCD orchestration, mode switching
│   ├── fan.py         # FanService — fan monitoring, duty control, curves
│   ├── sensor.py      # SensorService — hardware sensor collection + cache
│   ├── theme.py       # ThemeService — theme CRUD, config parsing
│   └── media.py       # MediaService — video/GIF frame extraction
├── protocols/         # Hardware protocol implementations (ADB, TCP, HID)
├── infrastructure/    # Config persistence, logging, system sensor backends
│   ├── theme_xml_parser.py  # Zero-dep XML parse/serialize for Theme*.xml
│   ├── theme_repository.py  # FileThemeRepository — bundled + user theme dirs
│   └── platform.py          # OS detection, config_dir(), data_dir(), etc.
├── adapters/
│   ├── cli/           # Typer CLI — thin wrapper calling services
│   ├── gui/           # PySide6 GUI — pages, widgets, theme editor
│   └── api/           # FastAPI REST — optional [api] extra
└── __version__.py
```

### GUI Structure
```
adapters/gui/
├── main_window.py          # Frameless 1400x800 window, titlebar, nav tabs
├── constants.py            # Layout dims, color palette, asset paths, resolve_theme_font()
├── pages/
│   ├── page_hardware.py    # Sensor dashboard + fan status
│   ├── page_theme.py       # 3-panel: preview | thumbnails | sensor cards
│   ├── page_theme_editor.py # Interactive QGraphicsScene theme editor
│   └── page_settings.py    # 2-column: settings | version panel
└── widgets/
    ├── lcd_preview.py      # 480x480 QPainter renderer (scalable via display_size)
    ├── canvas_scene.py     # EditorScene + CanvasItem/ImageItem/TextItem
    ├── property_panel.py   # Property editor for selected canvas item
    ├── element_toolbar.py  # Add/delete/duplicate/z-order toolbar
    ├── image_crop_dialog.py # PIL-based crop/rotate to 480x480
    ├── undo_commands.py    # QUndoCommand subclasses (Move, Add, Delete, ZOrder, Property)
    ├── theme_card.py       # 60x60 theme thumbnail with selection
    ├── sensor_card.py      # Hardware page sensor row (bg_hw_row.png)
    └── image_button.py     # Clickable PNG label with hover opacity
```

### Design Patterns
- **Dependency Injection**: Services receive ports in constructor, never import adapters
- **Repository Pattern**: ThemeRepositoryPort abstracts file/DB/remote storage
- **Abstract Base Classes**: Ports define contracts adapters must implement
- **Strategy Pattern**: Fan curves, display modes swappable at runtime
- **Observer Pattern**: EventBus broadcasts state changes, GUI subscribes

## Source Material
- **Decompiled C# source**: `decompiled/WFanManager/` (125 files from WFanManager.exe)
- **Decompiled XAML**: `dev/tools/baml-decompiler/xaml-output/` (28 BAML→XAML files)
  - `view/pageyj.xaml` — theme page layout (the primary reference for Display Settings)
  - `view/pagesz.xaml` — settings page layout
  - `view/mainwindow.xaml` — main window structure
  - `assets/styles/sliderstyle.xaml` — slider styling (#847148 accent, white thumb)
  - `assets/styles/pagedictionary.xaml` — toggle/radio styles (#02d0e8 cyan checked)
  - `assets/styles/buttondictionary.xaml` — button hover (opacity 0.55)
  - `usercontrols/uccard.xaml` — sensor card (100x100, white border, CornerRadius=5)
- **Installed Windows app**: `TR-VISION HOME/` (DLLs, assets, configs)
- **The C# is a reference for WHAT the hardware does, not HOW to write our code**
- **The XAML is the source of truth for layout dimensions, colors, and styling**

## XAML Color Palette (from decompiled styles)
- `#847148` — primary accent (borders, slider fill, selected states, language combo bg)
- `#02d0e8` — cyan (toggle/radio checked state)
- `#ededed` — primary text
- `#dddddd` — secondary text (brightness value)
- `#222222` — input backgrounds
- `#363636` — input hover
- `#717171` — disabled text, inactive tab foreground
- `#b6b6b6` — slider track background
- `#ffffff` — theme card borders, button text

## Font Handling — WPF DIPs to Qt Points
WPF uses DIPs (1/96"), Qt uses points (1/72"). Conversion: `pts = round(dips * 0.75)`.
Use `resolve_theme_font()` in `constants.py` — never duplicate the conversion logic.
LCDPreview renders at full 480x480 internally, uses `setScaledContents(True)` to display
at smaller sizes (e.g., 300x300 on theme page), matching WPF Viewbox behavior.

## Platform Support
- **Linux**: All non-EOL distros (Ubuntu 20.04+, Fedora, Debian, Arch, openSUSE, etc.)
- **macOS**: 10.15+
- **Windows**: 10+
- **BSD**: FreeBSD, OpenBSD, NetBSD
- Use `trcc_vision.infrastructure.platform` for OS detection and path resolution
- Never hardcode platform-specific paths — use `config_dir()`, `data_dir()`, `cache_dir()`, `log_dir()`
- Test platform-specific code with mocked `sys.platform`, not `sys.platform` checks in tests

## Conventions
- **Logging**: `log = logging.getLogger(__name__)` — never `print()` for diagnostics. Actually USE the logger at key interaction points, not just declare it.
- **Paths**: `pathlib.Path` everywhere, cross-platform via `infrastructure.platform`
- **Type hints**: On all public APIs
- **Tests**: `pytest` with `PYTHONPATH=src` — currently 264 tests
- **Linting**: `ruff check .` must pass before any commit
- **Python**: ≥3.10, use `from __future__ import annotations` for modern type syntax. No StrEnum (3.11+) — use `StrEnum(str, Enum)` backport in `core/enums.py`

## Development Workflow
- **Default branch**: `stable`
- **GitHub**: `Lexonight1/trcc-vision` (private)
- **Never push without explicit user instruction**
- Commit freely during development, no version bump until release
- `ruff check .` before each commit
- **BAML decompiler**: `dev/tools/baml-decompiler/` — run via `dotnet run` with Baml2Xaml to decompile .baml from WFanManager.exe

## Style
- KISS — minimal complexity, no over-engineering
- OOP — classes with clear single responsibilities
- DRY — extract helpers for repeated patterns, inline one-off logic
- Type hints on all public APIs
- NamedTuple/dataclass over raw tuples/dicts
