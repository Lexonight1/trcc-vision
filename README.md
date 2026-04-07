# TR-VISION HOME

Cross-platform fan controller and LCD screen manager for Thermalright TR-VISION devices.

The original TR-VISION HOME app is Windows-only. This project replaces it with a native, cross-platform application that runs on **Linux, macOS, Windows, and BSD** — no Wine, no VM, no workarounds.

## Status

**Pre-alpha** (v0.1.0) — architecture is in place, hardware communication is being wired up.

## Features (planned)

- GUI (PySide6) — theme browser, LCD preview, sensor dashboard, theme editor
- CLI (Typer) — full command-line control
- REST API (FastAPI) — optional headless/remote control
- Theme management — browse, load, save, edit, import/export
- LCD display — push images, video, GIFs to the device screen
- Sensor overlay — CPU/GPU temp, load, fan RPM, RAM, disk usage
- Fan control — manual duty, auto curves
- Cross-platform ADB — platform-specific binary resolution for Linux, macOS, Windows, BSD

## Architecture

Hexagonal (ports & adapters), SOLID, dependency-injected Python.

```
src/trcc_vision/
├── core/           # Domain models, enums, ports (ABCs), use cases
├── services/       # Business logic — device, display, fan, sensor, theme, media
├── protocols/      # Hardware communication — ADB (per-platform), TCP, message framing
├── infrastructure/ # Config, logging, sensors, theme persistence, platform detection
└── adapters/
    ├── gui/        # PySide6 desktop app
    ├── cli/        # Typer CLI
    └── api/        # FastAPI REST
```

Device communication uses ADB + TCP:
1. ADB discovers and connects to the TR-VISION device
2. ADB sets up port forwarding
3. TCP client sends framed messages (commands, sensor data, LCD frames)
4. ADB pushes files (themes, images) to device storage

## Requirements

- Python 3.10+
- ADB (`android-tools`, Homebrew `android-platform-tools`, or bundled on Windows)
- PySide6 (for GUI)

## Install

```bash
# Clone
git clone https://github.com/Lexonight1/trcc-vision.git
cd trcc-vision

# Install with GUI
pip install -e ".[gui,sensors]"

# Or minimal (CLI only)
pip install -e ".[sensors]"

# Development
pip install -e ".[dev,gui,sensors]"
```

## Usage

```bash
# Launch GUI
trcc-vision gui

# CLI
trcc-vision detect
trcc-vision connect <device-address>
trcc-vision theme list
trcc-vision theme load <name>
```

## ADB Setup

The app auto-detects the ADB binary per platform:

| Platform | Where it looks |
|----------|---------------|
| Linux | System PATH (`apt install adb`), `~/Android/Sdk/platform-tools/` |
| macOS | System PATH, Homebrew (`/opt/homebrew/bin/`, `/usr/local/bin/`), `~/Library/Android/sdk/` |
| Windows | Bundled `assets/adb/adb.exe`, System PATH, `%LOCALAPPDATA%\Android\Sdk\` |
| BSD | System PATH, `/usr/local/bin/` (ports) |

## Development

```bash
# Run tests
PYTHONPATH=src pytest -v

# Lint
ruff check .

# Type check
pyright
```

278 tests, all passing.

## Related

- [thermalright-trcc-linux](https://github.com/Lexonight1/thermalright-trcc-linux) — sister project for Thermalright SCSI/HID coolers (Linux/macOS/BSD)

## License

GPL-3.0-or-later

## Disclaimer

Unofficial community project. Not affiliated with Thermalright.
