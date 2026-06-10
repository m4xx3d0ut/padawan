from __future__ import annotations

from padawan.settings import Settings, default_content_dir, default_docs_dir, ensure_settings_dirs


def test_default_paths_prefer_current_working_tree(monkeypatch, tmp_path) -> None:
    content_dir = tmp_path / "content" / "courses"
    docs_dir = tmp_path / "docs" / "wiki"
    content_dir.mkdir(parents=True)
    docs_dir.mkdir(parents=True)

    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("PADAWAN_CONTENT_DIR", raising=False)
    monkeypatch.delenv("PADAWAN_DOCS_DIR", raising=False)

    assert default_content_dir() == content_dir
    assert default_docs_dir() == docs_dir


def test_ensure_settings_dirs_creates_user_data_dirs(tmp_path) -> None:
    settings = Settings(state_dir=tmp_path)

    ensure_settings_dirs(settings)

    assert settings.user_course_dir.is_dir()
    assert settings.course_draft_dir.is_dir()
    assert settings.backup_dir.is_dir()
