from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from padawan.backup import BackupError, export_backup, import_backup, inspect_backup
from padawan.courses import export_course, load_courses
from padawan.models import TRAINING_DATA_FORMAT, RuntimeResult
from padawan.settings import REPO_ROOT, Settings, ensure_settings_dirs
from padawan.storage import Storage


def make_settings(tmp_path: Path) -> Settings:
    settings = Settings(
        state_dir=tmp_path,
        content_dir=REPO_ROOT / "content" / "courses",
        docs_dir=REPO_ROOT / "docs" / "wiki",
    )
    ensure_settings_dirs(settings)
    return settings


def test_backup_export_and_restore_safe_merge(tmp_path: Path) -> None:
    settings = make_settings(tmp_path / "source")
    storage = Storage(settings.db_path)
    course = load_courses(settings.content_dir)["python-basics"]
    local_course = course.model_copy(update={"id": "local-python"})
    draft_course = course.model_copy(update={"id": "draft-python", "verified": False})

    storage.record_attempt(course, course.lessons[0].id, RuntimeResult(status="passed"))
    storage.upsert_codex_thread(
        thread_id="thread-1",
        course_id=course.id,
        lesson_id=course.lessons[0].id,
        title="Python Basics: Hello Python",
    )
    export_course(local_course, settings.user_course_dir / "local-python.json")
    export_course(draft_course, settings.course_draft_dir / "draft-python.json")

    archive = tmp_path / "padawan.zip"
    summary = export_backup(settings, archive)
    inspected = inspect_backup(archive)

    assert summary.table_counts["attempts"] == 1
    assert summary.table_counts["codex_threads"] == 1
    assert inspected.courses == ["local-python"]
    assert inspected.drafts == ["draft-python"]

    target = make_settings(tmp_path / "target")
    restored = import_backup(target, archive)
    restored_again = import_backup(target, archive)

    assert restored.pre_restore_backup is not None
    assert restored.table_inserted["attempts"] == 1
    assert restored.imported_courses == ["local-python"]
    assert restored.imported_drafts == ["draft-python"]
    assert restored_again.table_inserted["attempts"] == 0
    assert restored_again.table_skipped["attempts"] == 1
    assert Storage(target.db_path).codex_thread("thread-1") is not None
    assert (target.user_course_dir / "local-python.json").exists()
    assert (target.course_draft_dir / "draft-python.json").exists()
    restored_courses = load_courses(target.user_course_dir)
    restored_lesson = restored_courses["local-python"].lessons[0]
    assert restored_courses["local-python"].schema_version == TRAINING_DATA_FORMAT
    assert restored_lesson.examples
    assert restored_lesson.exercises


def test_backup_import_dry_run_does_not_write(tmp_path: Path) -> None:
    settings = make_settings(tmp_path / "source")
    course = load_courses(settings.content_dir)["python-basics"].model_copy(
        update={"id": "local-python"}
    )
    export_course(course, settings.user_course_dir / "local-python.json")
    archive = export_backup(settings, tmp_path / "dry.zip").archive
    target = make_settings(tmp_path / "target")

    summary = import_backup(target, archive, dry_run=True)

    assert summary.dry_run is True
    assert summary.imported_courses == ["local-python"]
    assert not (target.user_course_dir / "local-python.json").exists()


def test_backup_rejects_unsafe_members(tmp_path: Path) -> None:
    archive = tmp_path / "bad.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("../evil.json", "{}")

    with pytest.raises(BackupError):
        inspect_backup(archive)
