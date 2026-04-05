"""Tests for i18n — JSON locale loading, translation, fallback."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from trcc_vision.infrastructure.i18n import I18n, detect_system_language


@pytest.fixture()
def locales_dir(tmp_path: Path) -> Path:
    """Create temp locale directory with en.json and zh.json."""
    en = {
        "app.name": "TestApp",
        "greeting": "Hello {name}",
        "only_english": "English only",
    }
    zh = {
        "app.name": "测试应用",
        "greeting": "你好 {name}",
    }
    (tmp_path / "en.json").write_text(json.dumps(en), encoding="utf-8")
    (tmp_path / "zh.json").write_text(json.dumps(zh), encoding="utf-8")
    return tmp_path


@pytest.fixture()
def i18n(locales_dir: Path) -> I18n:
    """I18n instance with test locales."""
    return I18n(locales_dir=locales_dir)


class TestI18nBasic:
    def test_default_is_english(self, i18n: I18n) -> None:
        assert i18n.current_language() == "en"

    def test_translate_english(self, i18n: I18n) -> None:
        assert i18n.t("app.name") == "TestApp"

    def test_translate_with_interpolation(self, i18n: I18n) -> None:
        assert i18n.t("greeting", name="World") == "Hello World"


class TestI18nLanguageSwitch:
    def test_switch_to_chinese(self, i18n: I18n) -> None:
        i18n.set_language("zh")
        assert i18n.current_language() == "zh"
        assert i18n.t("app.name") == "测试应用"

    def test_chinese_interpolation(self, i18n: I18n) -> None:
        i18n.set_language("zh")
        assert i18n.t("greeting", name="世界") == "你好 世界"


class TestI18nFallback:
    def test_missing_key_in_zh_falls_back_to_en(self, i18n: I18n) -> None:
        i18n.set_language("zh")
        # "only_english" exists in en.json but not zh.json
        assert i18n.t("only_english") == "English only"

    def test_completely_missing_key_returns_key(self, i18n: I18n) -> None:
        assert i18n.t("nonexistent.key") == "nonexistent.key"

    def test_switch_to_unknown_locale_keeps_current(self, i18n: I18n) -> None:
        i18n.set_language("xx")  # doesn't exist
        assert i18n.current_language() == "en"


class TestI18nAvailableLanguages:
    def test_lists_en_and_zh(self, i18n: I18n) -> None:
        langs = i18n.available_languages()
        assert "en" in langs
        assert "zh" in langs

    def test_switch_back_to_english(self, i18n: I18n) -> None:
        i18n.set_language("zh")
        i18n.set_language("en")
        assert i18n.t("app.name") == "TestApp"


class TestI18nNormalize:
    def test_normalizes_locale_codes(self, i18n: I18n) -> None:
        i18n.set_language("zh_CN")
        assert i18n.current_language() == "zh"

    def test_normalizes_bcp47(self, i18n: I18n) -> None:
        i18n.set_language("zh-Hans")
        assert i18n.current_language() == "zh"


class TestI18nRealLocales:
    """Test against the actual bundled locale files."""

    def test_english_locale_loads(self) -> None:
        i18n = I18n()
        assert i18n.t("app.name") == "TR-VISION HOME"

    def test_chinese_locale_loads(self) -> None:
        i18n = I18n()
        i18n.set_language("zh")
        assert i18n.t("sensor.cpu_temp") == "CPU温度"

    def test_english_fallback_for_chinese(self) -> None:
        i18n = I18n()
        i18n.set_language("zh")
        # Both locales should have this key
        assert "TR-VISION" in i18n.t("app.name")


class TestDetectSystemLanguage:
    def test_returns_string(self) -> None:
        lang = detect_system_language()
        assert isinstance(lang, str)
        assert len(lang) >= 2


class TestI18nFormatErrors:
    def test_bad_format_returns_raw_string(self, i18n: I18n) -> None:
        # Pass wrong kwargs — should return unformatted string, not crash
        result = i18n.t("greeting", wrong_key="oops")
        assert result == "Hello {name}"
