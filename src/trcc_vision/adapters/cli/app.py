"""Typer CLI adapter — thin wrapper that calls use cases via AppContext.

Every command: create/reuse AppContext → call use case → format output.
No business logic lives here — only argument parsing and text formatting.
All user-facing strings go through t() for i18n.
"""

from __future__ import annotations

import logging

import typer

from trcc_vision.__version__ import __version__
from trcc_vision.infrastructure.i18n import setup_i18n, t

log = logging.getLogger(__name__)

app = typer.Typer(
    name="trcc-vision",
    no_args_is_help=True,
)

# Lazy singleton — created on first command that needs it
_ctx = None
_mock_mode = False


def _get_ctx():  # noqa: ANN202
    """Get or create the shared AppContext."""
    global _ctx  # noqa: PLW0603
    if _ctx is None:
        from trcc_vision.core.context import AppContext
        _ctx = AppContext(mock=_mock_mode)
    return _ctx


def _ensure_connected(address: str | None = None) -> None:
    """Ensure a device is connected — by address, saved state, or auto-detect.

    Priority: explicit address > persisted last device > single-device auto-detect.
    Raises typer.Exit(1) if no device can be connected.
    """
    ctx = _get_ctx()
    if ctx.device_service is None:
        typer.echo("Device service not available")
        raise typer.Exit(1)

    if ctx.device_service.is_connected:
        return

    # 1. Explicit address provided
    if address:
        from trcc_vision.core.enums import ConnectionType
        from trcc_vision.core.models import DeviceInfo

        device = DeviceInfo(
            name=f"TR-VISION ({address})",
            connection=ConnectionType.ADB,
            address=address,
        )
        try:
            ctx.device_service.select(device)
            return
        except Exception as e:
            typer.echo(f"Connection failed: {e}")
            raise typer.Exit(1) from None

    # 2. Reconnect to last known device
    if ctx.device_service.reconnect_last():
        log.info("Reconnected to last device")
        return

    # 3. Auto-detect if exactly one device found
    devices = ctx.device_service.detect()
    if len(devices) == 1:
        try:
            ctx.device_service.select(devices[0])
            log.info("Auto-connected to %s", devices[0].name)
            return
        except Exception:
            pass

    typer.echo("No device connected. Use --device/-d or 'trcc-vision connect' first.")
    raise typer.Exit(1)


def _setup_logging(verbose: bool, quiet: bool, log_file: str | None) -> None:
    """Configure logging based on CLI flags."""
    from pathlib import Path

    from trcc_vision.infrastructure.logging import setup_logging

    if verbose:
        console_level = logging.DEBUG
    elif quiet:
        console_level = logging.WARNING
    else:
        console_level = logging.INFO

    setup_logging(
        console_level=console_level,
        log_file=Path(log_file) if log_file else None,
    )


@app.callback()
def common(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="DEBUG logging to console"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="WARNING-only console output"),
    log_file: str | None = typer.Option(None, "--log-file", help="Override log file path"),
    lang: str | None = typer.Option(None, "--lang", help="Language override (en, zh, de, etc.)"),
    mock: bool = typer.Option(False, "--mock", help="Mock device mode (no hardware needed)"),
) -> None:
    """TR-VISION HOME CLI."""
    global _mock_mode  # noqa: PLW0603
    _mock_mode = mock
    _setup_logging(verbose, quiet, log_file)
    setup_i18n(lang)


# ── Commands ────────────────────────────────────────────────────────────


@app.command()
def version() -> None:
    """Show version."""
    typer.echo(t("cli.version", version=__version__))


@app.command()
def detect() -> None:
    """Scan for connected TR-VISION devices."""
    log.info("detect command invoked")
    ctx = _get_ctx()
    if ctx.detect_devices is None:
        typer.echo(t("cli.detect.not_available"))
        return
    typer.echo(t("cli.detect.scanning"))
    devices = ctx.detect_devices.execute()
    if not devices:
        typer.echo(t("cli.detect.none_found"))
        return
    for d in devices:
        typer.echo(f"  {d.name}  {d.connection.value}  {d.address}  {d.lcd_width}x{d.lcd_height}")


@app.command()
def sensors() -> None:
    """Read and display hardware sensor values."""
    log.info("sensors command invoked")
    ctx = _get_ctx()
    readings = ctx.read_all_sensors.execute()
    if not readings:
        typer.echo(t("cli.sensors.none"))
        return
    for r in readings:
        typer.echo(f"  {r.label:<20s} {r.value:>8.1f} {r.unit}")


@app.command()
def fans() -> None:
    """Read and display fan channel states."""
    log.info("fans command invoked")
    ctx = _get_ctx()
    if ctx.get_fan_states is None:
        typer.echo("Fan monitoring not available (use --mock for simulated fans)")
        return
    states = ctx.get_fan_states.execute()
    if not states:
        typer.echo("No fan channels found")
        return
    for s in states:
        typer.echo(f"  Fan {s.channel}:  {s.rpm:>5d} RPM  {s.duty_percent:>3d}%  [{s.mode.value}]")


@app.command()
def doctor() -> None:
    """Check dependencies and system configuration."""
    log.info("doctor command invoked")
    ctx = _get_ctx()
    results = ctx.run_doctor.execute()
    for r in results:
        status = t("doctor.pass") if r.passed else t("doctor.fail")
        typer.echo(f"  [{status}] {r.name}: {r.detail}")
    passed = sum(1 for r in results if r.passed)
    typer.echo(f"\n{t('cli.doctor.passed', passed=passed, total=len(results))}")


@app.command()
def info() -> None:
    """Show system and application information."""
    log.info("info command invoked")
    ctx = _get_ctx()
    si = ctx.get_system_info.execute()
    typer.echo(f"  {t('cli.info.version', version=si.app_version)}")
    typer.echo(f"  {t('cli.info.python', python=si.python_version.split()[0])}")
    typer.echo(f"  {t('cli.info.platform', platform=si.platform_name)}")
    typer.echo(f"  {t('cli.info.os', os=si.os_version)}")
    typer.echo(f"  {t('cli.info.machine', machine=si.machine)}")


@app.command()
def connect(
    address: str = typer.Argument(..., help="Device address (IP:port or ADB serial)"),
) -> None:
    """Connect to a TR-VISION device."""
    log.info("connect command: %s", address)
    ctx = _get_ctx()
    if ctx.device_service is None:
        typer.echo("Device service not available")
        raise typer.Exit(1)

    # Detect first, find matching device or create one
    from trcc_vision.core.enums import ConnectionType
    from trcc_vision.core.models import DeviceInfo

    device = DeviceInfo(
        name=f"TR-VISION ({address})",
        connection=ConnectionType.ADB,
        address=address,
    )
    try:
        ctx.device_service.select(device)
        typer.echo(f"Connected to {device.name}")
    except Exception as e:
        typer.echo(f"Connection failed: {e}")
        raise typer.Exit(1) from None


@app.command(name="send-image")
def send_image(
    image_path: str = typer.Argument(..., help="Path to image file (PNG, JPG, etc.)"),
    address: str | None = typer.Option(
        None, "--device", "-d", help="Device address",
    ),
) -> None:
    """Send an image to the LCD display."""
    from pathlib import Path

    log.info("send-image command: %s", image_path)
    ctx = _get_ctx()
    if ctx.display_service is None:
        typer.echo("Display service not available")
        raise typer.Exit(1)
    _ensure_connected(address)

    img_path = Path(image_path)
    if not img_path.is_file():
        typer.echo(f"File not found: {image_path}")
        raise typer.Exit(1)

    try:
        from PIL import Image

        img = Image.open(img_path)
        ctx.display_service.send_image(img)
        typer.echo(f"Image sent to LCD: {img_path.name} ({img.width}x{img.height})")
    except ImportError:
        typer.echo("Pillow not installed (pip install Pillow)")
        raise typer.Exit(1) from None
    except Exception as e:
        typer.echo(f"Failed to send image: {e}")
        raise typer.Exit(1) from None


@app.command(name="set-brightness")
def set_brightness_cmd(
    level: int = typer.Argument(..., help="Brightness level (0-100)"),
    address: str | None = typer.Option(None, "--device", "-d", help="Device address"),
) -> None:
    """Set LCD brightness."""
    log.info("set-brightness command: %d", level)
    ctx = _get_ctx()
    if ctx.display_service is None:
        typer.echo("Display service not available")
        raise typer.Exit(1)
    _ensure_connected(address)
    ctx.display_service.set_brightness(level)
    typer.echo(f"Brightness set to {level}%")


@app.command(name="screen")
def screen_cmd(
    state: str = typer.Argument(..., help="'on' or 'off'"),
    address: str | None = typer.Option(None, "--device", "-d", help="Device address"),
) -> None:
    """Turn LCD screen on or off."""
    ctx = _get_ctx()
    if ctx.display_service is None:
        typer.echo("Display service not available")
        raise typer.Exit(1)
    _ensure_connected(address)
    on = state.lower() in ("on", "1", "true")
    ctx.display_service.screen_power(on)
    typer.echo(f"Screen turned {'on' if on else 'off'}")


@app.command()
def disconnect() -> None:
    """Disconnect from current device."""
    ctx = _get_ctx()
    if ctx.device_service is None:
        typer.echo("Device service not available")
        return
    ctx.device_service.disconnect()
    typer.echo("Disconnected")


@app.command()
def gui() -> None:
    """Launch the PySide6 GUI."""
    log.info("gui command invoked (mock=%s)", _mock_mode)
    try:
        from trcc_vision.adapters.gui import app as gui_app  # noqa: F811

        gui_app.run(mock=_mock_mode)
    except ImportError:
        log.error("PySide6 not installed")
        typer.echo(t("cli.gui.missing_pyside6"))
        raise typer.Exit(1) from None


@app.command()
def serve(
    host: str = "0.0.0.0",
    port: int = 8080,
) -> None:
    """Start the REST API server."""
    log.info("serve command invoked: host=%s port=%d", host, port)
    try:
        import uvicorn

        from trcc_vision.adapters.api.server import create_app

        uvicorn.run(create_app(), host=host, port=port)
    except ImportError:
        log.error("fastapi/uvicorn not installed")
        typer.echo(t("cli.api.missing_deps"))
        raise typer.Exit(1) from None


def main() -> None:
    app()


if __name__ == "__main__":
    main()
