"""Tests for file-based theme repository."""

from __future__ import annotations

from pathlib import Path

import pytest

from trcc_vision.infrastructure.theme_repository import FileThemeRepository


@pytest.fixture()
def repo(tmp_path: Path) -> FileThemeRepository:
    """Theme repo with bundled + user dirs in tmp."""
    bundled = tmp_path / "bundled"
    user = tmp_path / "user"
    bundled.mkdir()
    user.mkdir()

    # Create 2 bundled themes
    (bundled / "Theme1.xml").write_text("<ThemeModel><Name>T1</Name></ThemeModel>")
    (bundled / "Theme2.xml").write_text("<ThemeModel><Name>T2</Name></ThemeModel>")
    (bundled / "Theme1.png").write_bytes(b"fake png")

    return FileThemeRepository(bundled, user)


class TestListThemes:
    def test_lists_bundled(self, repo: FileThemeRepository) -> None:
        themes = repo.list_themes()
        assert len(themes) == 2
        names = [t.name for t in themes]
        assert "Theme1.xml" in names
        assert "Theme2.xml" in names

    def test_lists_user_themes_too(self, repo: FileThemeRepository, tmp_path: Path) -> None:
        user_dir = tmp_path / "user"
        (user_dir / "Custom.xml").write_text("<ThemeModel><Name>Custom</Name></ThemeModel>")
        themes = repo.list_themes()
        assert len(themes) == 3

    def test_empty_dirs(self, tmp_path: Path) -> None:
        repo = FileThemeRepository(tmp_path / "none1", tmp_path / "none2")
        assert repo.list_themes() == []


class TestLoadThemeConfig:
    def test_loads_bytes(self, repo: FileThemeRepository, tmp_path: Path) -> None:
        path = tmp_path / "bundled" / "Theme1.xml"
        data = repo.load_theme_config(path)
        assert b"<ThemeModel>" in data
        assert b"T1" in data


class TestSaveThemeConfig:
    def test_saves_to_user_dir(self, repo: FileThemeRepository, tmp_path: Path) -> None:
        user_dir = tmp_path / "user"
        save_path = user_dir / "NewTheme.xml"
        repo.save_theme_config(save_path, b"<ThemeModel><Name>New</Name></ThemeModel>")
        assert save_path.exists()
        assert b"New" in save_path.read_bytes()

    def test_redirects_bundled_save_to_user(
        self, repo: FileThemeRepository, tmp_path: Path,
    ) -> None:
        bundled_path = tmp_path / "bundled" / "Theme1.xml"
        repo.save_theme_config(bundled_path, b"<ThemeModel><Name>Modified</Name></ThemeModel>")
        # Should save to user dir, not bundled
        user_copy = tmp_path / "user" / "Theme1.xml"
        assert user_copy.exists()

    def test_creates_user_dir_if_missing(self, tmp_path: Path) -> None:
        repo = FileThemeRepository(tmp_path / "bundled", tmp_path / "new_user")
        save_path = tmp_path / "new_user" / "Test.xml"
        repo.save_theme_config(save_path, b"<data/>")
        assert save_path.exists()


class TestDeleteTheme:
    def test_deletes_user_theme(self, repo: FileThemeRepository, tmp_path: Path) -> None:
        user_dir = tmp_path / "user"
        theme = user_dir / "Deletable.xml"
        theme.write_text("<data/>")
        assert theme.exists()
        repo.delete_theme(theme)
        assert not theme.exists()

    def test_refuses_to_delete_bundled(
        self, repo: FileThemeRepository, tmp_path: Path,
    ) -> None:
        bundled_theme = tmp_path / "bundled" / "Theme1.xml"
        assert bundled_theme.exists()
        repo.delete_theme(bundled_theme)
        assert bundled_theme.exists()  # still there

    def test_deletes_associated_preview(
        self, repo: FileThemeRepository, tmp_path: Path,
    ) -> None:
        user_dir = tmp_path / "user"
        xml = user_dir / "WithPreview.xml"
        png = user_dir / "WithPreview.png"
        xml.write_text("<data/>")
        png.write_bytes(b"fake png")
        repo.delete_theme(xml)
        assert not xml.exists()
        assert not png.exists()

    def test_missing_theme_is_safe(self, repo: FileThemeRepository, tmp_path: Path) -> None:
        repo.delete_theme(tmp_path / "user" / "nonexistent.xml")  # no crash
