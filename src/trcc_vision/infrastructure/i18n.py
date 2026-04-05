"""Internationalization — JSON locale files with fallback to English.

Usage:
    from trcc_vision.infrastructure.i18n import setup_i18n, t

    setup_i18n("zh")                    # or auto-detect from system locale
    print(t("cli.detect.scanning"))     # "正在扫描设备..."
    print(t("cli.version", version="1.0"))  # "trcc-vision 1.0"

Zero dependencies — stdlib json + locale only.
"""

from __future__ import annotations

import json
import locale
import logging
from pathlib import Path

log = logging.getLogger(__name__)

_LOCALES_DIR = Path(__file__).resolve().parent.parent / "locales"
_DEFAULT_LANG = "en"

_instance: I18n | None = None


class I18n:
    """Loads JSON locale files and resolves translation keys."""

    def __init__(
        self,
        locales_dir: Path | None = None,
        default_lang: str = _DEFAULT_LANG,
    ) -> None:
        self._locales_dir = locales_dir or _LOCALES_DIR
        self._default_lang = default_lang
        self._fallback: dict[str, str] = {}
        self._active: dict[str, str] = {}
        self._lang = default_lang

        # Always load English as fallback
        self._fallback = self._load_locale(default_lang)
        self._active = self._fallback
        log.debug(
            "I18n initialized: dir=%s, default=%s, %d keys",
            self._locales_dir, default_lang, len(self._fallback),
        )

    def set_language(self, lang: str) -> None:
        """Switch the active language. Falls back to English for missing keys."""
        lang = self._normalize(lang)
        if lang == self._lang:
            return

        if lang == self._default_lang:
            self._active = self._fallback
        else:
            loaded = self._load_locale(lang)
            if loaded:
                self._active = loaded
            else:
                log.warning("Locale '%s' not found, keeping '%s'", lang, self._lang)
                return

        self._lang = lang
        log.info("Language set to: %s (%d keys)", lang, len(self._active))

    def t(self, key: str, **kwargs: object) -> str:
        """Translate a key, with optional interpolation.

        Looks up in active locale first, falls back to English.
        Returns the key itself if not found anywhere (never crashes).
        """
        value = self._active.get(key) or self._fallback.get(key)
        if value is None:
            log.debug("Missing translation key: %s", key)
            return key

        if kwargs:
            try:
                return value.format_map(kwargs)
            except (KeyError, ValueError):
                log.warning("Format error for key '%s': %r", key, kwargs)
                return value

        return value

    def current_language(self) -> str:
        """Return the active language code."""
        return self._lang

    def available_languages(self) -> list[str]:
        """List all available language codes (from .json files in locales dir)."""
        if not self._locales_dir.exists():
            return [self._default_lang]
        return sorted(
            p.stem for p in self._locales_dir.glob("*.json")
        )

    def _load_locale(self, lang: str) -> dict[str, str]:
        """Load a locale JSON file. Returns empty dict if not found."""
        path = self._locales_dir / f"{lang}.json"
        if not path.exists():
            log.debug("Locale file not found: %s", path)
            return {}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            log.debug("Loaded locale '%s': %d keys from %s", lang, len(data), path)
            return data
        except (json.JSONDecodeError, OSError):
            log.exception("Failed to load locale: %s", path)
            return {}

    def _normalize(self, lang: str) -> str:
        """Normalize language code: 'zh_CN' → 'zh', 'en_US' → 'en'."""
        return lang.split("_")[0].split("-")[0].lower()


def detect_system_language() -> str:
    """Detect the system's preferred language."""
    try:
        # getlocale() is the non-deprecated replacement for getdefaultlocale()
        lang, _ = locale.getlocale()
        if lang:
            return lang.split("_")[0].lower()
    except (ValueError, AttributeError):
        pass
    # Fallback: check LANG/LC_ALL environment variables
    import os
    for var in ("LANG", "LC_ALL", "LC_MESSAGES", "LANGUAGE"):
        val = os.environ.get(var, "")
        if val and val != "C" and val != "POSIX":
            return val.split("_")[0].split(".")[0].lower()
    return _DEFAULT_LANG


def setup_i18n(lang: str | None = None) -> I18n:
    """Initialize the global i18n instance.

    Args:
        lang: Language code override. None = auto-detect from system locale.
    """
    global _instance  # noqa: PLW0603
    if _instance is not None and lang is None:
        return _instance

    _instance = I18n()
    resolved = lang or detect_system_language()
    _instance.set_language(resolved)
    log.info("i18n ready: lang=%s", _instance.current_language())
    return _instance


def t(key: str, **kwargs: object) -> str:
    """Translate a key using the global i18n instance.

    Auto-initializes with system locale if setup_i18n() hasn't been called.
    """
    global _instance  # noqa: PLW0603
    if _instance is None:
        _instance = I18n()
    return _instance.t(key, **kwargs)
