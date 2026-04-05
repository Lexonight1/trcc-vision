"""FastAPI REST adapter — thin wrapper calling use cases via AppContext.

Every endpoint: call use case → return JSON. No business logic here.
User-facing error messages go through t() for i18n.
Optional install: pip install trcc-vision[api]
"""

from __future__ import annotations

import logging
from dataclasses import asdict

from trcc_vision.__version__ import __version__
from trcc_vision.infrastructure.i18n import setup_i18n, t

log = logging.getLogger(__name__)


def create_app(mock: bool | None = None):  # noqa: ANN201
    """Factory for the FastAPI app, wired to AppContext."""
    import os

    from trcc_vision.infrastructure.logging import setup_logging

    setup_logging(console_level=logging.INFO)
    setup_i18n()

    if mock is None:
        mock = os.environ.get("TRIVISION_MOCK", "").lower() in ("1", "true", "yes")

    log.info("Creating TR-VISION API app (mock=%s)", mock)

    from fastapi import FastAPI

    from trcc_vision.core.context import AppContext

    ctx = AppContext(mock=mock)

    api = FastAPI(
        title=t("app.name"),
        description=t("app.description"),
        version=__version__,
    )

    @api.get("/health")
    def health() -> dict:
        log.debug("GET /health")
        return {"status": "ok", "version": __version__}

    @api.get("/info")
    def system_info() -> dict:
        log.debug("GET /info")
        return asdict(ctx.get_system_info.execute())

    @api.get("/sensors")
    def read_sensors() -> dict:
        log.debug("GET /sensors")
        readings = ctx.read_all_sensors.execute()
        return {"sensors": [asdict(r) for r in readings]}

    @api.get("/devices")
    def list_devices() -> dict:
        log.debug("GET /devices")
        if ctx.detect_devices is None:
            return {"devices": [], "error": t("api.device.not_available")}
        devices = ctx.detect_devices.execute()
        return {"devices": [asdict(d) for d in devices]}

    @api.get("/doctor")
    def run_doctor() -> dict:
        log.debug("GET /doctor")
        results = ctx.run_doctor.execute()
        return {
            "checks": [asdict(r) for r in results],
            "passed": sum(1 for r in results if r.passed),
            "total": len(results),
        }

    log.info("API app created with %d routes", len(api.routes))
    return api
