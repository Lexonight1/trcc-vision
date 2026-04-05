"""System use cases — info, report, doctor."""

from __future__ import annotations

import logging
import platform
import sys
from dataclasses import dataclass

from trcc_vision.__version__ import __version__
from trcc_vision.infrastructure.platform import current_platform

log = logging.getLogger(__name__)


@dataclass
class SystemInfo:
    """Basic system information."""

    app_version: str
    python_version: str
    platform_name: str
    os_version: str
    machine: str


@dataclass
class CheckResult:
    """Single dependency check result."""

    name: str
    passed: bool
    detail: str


class GetSystemInfo:
    """Get application and system information."""

    def execute(self) -> SystemInfo:
        log.debug("Gathering system info")
        info = SystemInfo(
            app_version=__version__,
            python_version=sys.version,
            platform_name=current_platform().value,
            os_version=platform.platform(),
            machine=platform.machine(),
        )
        log.info(
            "System: trcc-vision %s, Python %s, %s",
            info.app_version, sys.version.split()[0], info.platform_name,
        )
        return info


class RunDoctor:
    """Check all dependencies and report pass/fail."""

    def execute(self) -> list[CheckResult]:
        log.info("Running doctor checks...")
        results: list[CheckResult] = []

        results.append(self._check_python())
        results.append(self._check_import("PIL", "Pillow"))
        results.append(self._check_import("numpy", "numpy"))
        results.append(self._check_import("typer", "typer"))
        results.append(self._check_import("PySide6", "PySide6 (optional, for GUI)"))
        results.append(self._check_import("fastapi", "FastAPI (optional, for API)"))
        results.append(self._check_import("psutil", "psutil (optional, for sensors)"))
        results.append(self._check_binary("adb", "Android Debug Bridge"))
        results.append(self._check_binary("ffmpeg", "FFmpeg (optional, for video)"))

        passed = sum(1 for r in results if r.passed)
        total = len(results)
        log.info("Doctor: %d/%d checks passed", passed, total)
        return results

    def _check_python(self) -> CheckResult:
        ver = sys.version_info
        ok = ver >= (3, 10)
        return CheckResult(
            name="Python >= 3.10",
            passed=ok,
            detail=f"{ver.major}.{ver.minor}.{ver.micro}",
        )

    def _check_import(self, module: str, label: str) -> CheckResult:
        try:
            __import__(module)
            return CheckResult(name=label, passed=True, detail="installed")
        except ImportError:
            return CheckResult(name=label, passed=False, detail="not found")

    def _check_binary(self, name: str, label: str) -> CheckResult:
        import shutil

        path = shutil.which(name)
        if path:
            return CheckResult(name=label, passed=True, detail=path)
        return CheckResult(name=label, passed=False, detail="not in PATH")
