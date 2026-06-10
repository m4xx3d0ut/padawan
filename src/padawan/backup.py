from __future__ import annotations

import json
import sqlite3
import zipfile
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any

from . import __version__
from .courses import export_course, load_courses
from .models import Course, utc_now_iso
from .settings import Settings, ensure_settings_dirs
from .storage import Storage

BACKUP_FORMAT = "padawan.local-data"
BACKUP_VERSION = 1
STATE_TABLES = (
    "attempts",
    "progress_events",
    "badge_awards",
    "generation_jobs",
    "validation_runs",
)
MERGE_KEYS = {
    "attempts": (
        "course_id",
        "lesson_id",
        "status",
        "score_delta",
        "stdout",
        "stderr",
        "messages_json",
        "created_at",
    ),
    "progress_events": ("course_id", "lesson_id", "event_type", "payload_json", "created_at"),
    "badge_awards": ("course_id", "badge_id"),
    "generation_jobs": ("prompt", "status", "course_id", "detail", "created_at", "updated_at"),
    "validation_runs": ("course_id", "status", "detail", "created_at"),
}


class BackupError(ValueError):
    pass


@dataclass
class BackupSummary:
    archive: Path
    created_at: str = ""
    app_version: str = ""
    table_counts: dict[str, int] = field(default_factory=dict)
    courses: list[str] = field(default_factory=list)
    drafts: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "archive": str(self.archive),
            "created_at": self.created_at,
            "app_version": self.app_version,
            "table_counts": self.table_counts,
            "courses": self.courses,
            "drafts": self.drafts,
        }


@dataclass
class RestoreSummary:
    archive: Path
    dry_run: bool
    pre_restore_backup: Path | None = None
    table_inserted: dict[str, int] = field(default_factory=dict)
    table_skipped: dict[str, int] = field(default_factory=dict)
    imported_courses: list[str] = field(default_factory=list)
    imported_drafts: list[str] = field(default_factory=list)
    skipped_courses: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "archive": str(self.archive),
            "dry_run": self.dry_run,
            "pre_restore_backup": str(self.pre_restore_backup) if self.pre_restore_backup else None,
            "table_inserted": self.table_inserted,
            "table_skipped": self.table_skipped,
            "imported_courses": self.imported_courses,
            "imported_drafts": self.imported_drafts,
            "skipped_courses": self.skipped_courses,
        }


def default_backup_path(settings: Settings) -> Path:
    stamp = utc_now_iso().replace(":", "").replace("+", "Z")
    return settings.backup_dir / f"padawan-backup-{stamp}.zip"


def export_backup(settings: Settings, output_path: Path | None = None) -> BackupSummary:
    ensure_settings_dirs(settings)
    Storage(settings.db_path)
    archive = output_path or default_backup_path(settings)
    archive.parent.mkdir(parents=True, exist_ok=True)

    state = _export_state(settings.db_path)
    courses = _load_course_files(settings.user_course_dir)
    drafts = _load_course_files(settings.course_draft_dir)
    manifest = {
        "format": BACKUP_FORMAT,
        "version": BACKUP_VERSION,
        "created_at": utc_now_iso(),
        "app_version": __version__,
        "tables": {table: len(rows) for table, rows in state.items()},
        "courses": [course.id for _, course in courses],
        "drafts": [course.id for _, course in drafts],
    }

    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manifest.json", json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        zf.writestr("state.json", json.dumps(state, indent=2, sort_keys=True) + "\n")
        for _, course in courses:
            zf.writestr(f"courses/{course.id}.json", _course_json(course))
        for _, course in drafts:
            zf.writestr(f"course-drafts/{course.id}.json", _course_json(course))

    return BackupSummary(
        archive=archive,
        created_at=manifest["created_at"],
        app_version=manifest["app_version"],
        table_counts=manifest["tables"],
        courses=manifest["courses"],
        drafts=manifest["drafts"],
    )


def inspect_backup(archive: Path) -> BackupSummary:
    with zipfile.ZipFile(archive) as zf:
        _validate_member_names(zf)
        manifest = _read_manifest(zf)
        state = _read_state(zf)
        courses = [course.id for _, course in _read_course_members(zf, "courses")]
        drafts = [course.id for _, course in _read_course_members(zf, "course-drafts")]
    return BackupSummary(
        archive=archive,
        created_at=str(manifest.get("created_at", "")),
        app_version=str(manifest.get("app_version", "")),
        table_counts={table: len(state.get(table, [])) for table in STATE_TABLES},
        courses=courses,
        drafts=drafts,
    )


def import_backup(settings: Settings, archive: Path, *, dry_run: bool = False) -> RestoreSummary:
    ensure_settings_dirs(settings)
    Storage(settings.db_path)
    with zipfile.ZipFile(archive) as zf:
        _validate_member_names(zf)
        _read_manifest(zf)
        state = _read_state(zf)
        course_members = _read_course_members(zf, "courses")
        draft_members = _read_course_members(zf, "course-drafts")

    summary = RestoreSummary(archive=archive, dry_run=dry_run)
    seed_courses = load_courses(settings.content_dir)
    if dry_run:
        _summarize_import_targets(summary, seed_courses, course_members, draft_members)
        _summarize_tables(summary, state)
        return summary

    summary.pre_restore_backup = export_backup(settings).archive
    with sqlite3.connect(settings.db_path) as conn:
        conn.row_factory = sqlite3.Row
        for table in STATE_TABLES:
            inserted, skipped = _merge_table(conn, table, state.get(table, []))
            summary.table_inserted[table] = inserted
            summary.table_skipped[table] = skipped

    _write_course_members(
        settings.user_course_dir,
        seed_courses,
        course_members,
        imported=summary.imported_courses,
        skipped=summary.skipped_courses,
    )
    _write_course_members(
        settings.course_draft_dir,
        seed_courses,
        draft_members,
        imported=summary.imported_drafts,
        skipped=summary.skipped_courses,
    )
    return summary


def _export_state(db_path: Path) -> dict[str, list[dict[str, Any]]]:
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        state: dict[str, list[dict[str, Any]]] = {}
        for table in STATE_TABLES:
            rows = conn.execute(f"SELECT * FROM {table}").fetchall()  # noqa: S608
            state[table] = [dict(row) for row in rows]
        return state


def _load_course_files(directory: Path) -> list[tuple[Path, Course]]:
    courses: list[tuple[Path, Course]] = []
    if not directory.exists():
        return courses
    for path in sorted(directory.glob("*.json")):
        courses.append((path, Course.model_validate_json(path.read_text(encoding="utf-8"))))
    return courses


def _course_json(course: Course) -> str:
    return json.dumps(course.model_dump(), indent=2, sort_keys=True) + "\n"


def _validate_member_names(zf: zipfile.ZipFile) -> None:
    for name in zf.namelist():
        path = PurePosixPath(name)
        if path.is_absolute() or ".." in path.parts:
            raise BackupError(f"unsafe archive member: {name}")


def _read_manifest(zf: zipfile.ZipFile) -> dict[str, Any]:
    try:
        manifest = json.loads(zf.read("manifest.json").decode("utf-8"))
    except KeyError as exc:
        raise BackupError("backup is missing manifest.json") from exc
    except json.JSONDecodeError as exc:
        raise BackupError(f"invalid manifest.json: {exc}") from exc
    if manifest.get("format") != BACKUP_FORMAT:
        raise BackupError("unsupported backup format")
    if manifest.get("version") != BACKUP_VERSION:
        raise BackupError("unsupported backup version")
    return manifest


def _read_state(zf: zipfile.ZipFile) -> dict[str, list[dict[str, Any]]]:
    try:
        state = json.loads(zf.read("state.json").decode("utf-8"))
    except KeyError as exc:
        raise BackupError("backup is missing state.json") from exc
    except json.JSONDecodeError as exc:
        raise BackupError(f"invalid state.json: {exc}") from exc
    if not isinstance(state, dict):
        raise BackupError("state.json must be an object")
    return {
        table: rows if isinstance(rows := state.get(table, []), list) else []
        for table in STATE_TABLES
    }


def _read_course_members(zf: zipfile.ZipFile, prefix: str) -> list[tuple[str, Course]]:
    courses: list[tuple[str, Course]] = []
    for name in sorted(zf.namelist()):
        path = PurePosixPath(name)
        if len(path.parts) != 2 or path.parts[0] != prefix or path.suffix != ".json":
            continue
        try:
            courses.append((name, Course.model_validate_json(zf.read(name).decode("utf-8"))))
        except ValueError as exc:
            raise BackupError(f"invalid course backup member {name}: {exc}") from exc
    return courses


def _summarize_import_targets(
    summary: RestoreSummary,
    seed_courses: dict[str, Course],
    course_members: list[tuple[str, Course]],
    draft_members: list[tuple[str, Course]],
) -> None:
    for _, course in course_members:
        if course.id in seed_courses:
            summary.skipped_courses.append(f"{course.id} (seed conflict)")
        else:
            summary.imported_courses.append(course.id)
    for _, course in draft_members:
        if course.id in seed_courses:
            summary.skipped_courses.append(f"{course.id} (seed conflict)")
        else:
            summary.imported_drafts.append(course.id)


def _summarize_tables(summary: RestoreSummary, state: dict[str, list[dict[str, Any]]]) -> None:
    for table in STATE_TABLES:
        summary.table_inserted[table] = len(state.get(table, []))
        summary.table_skipped[table] = 0


def _merge_table(
    conn: sqlite3.Connection, table: str, rows: list[dict[str, Any]]
) -> tuple[int, int]:
    inserted = 0
    skipped = 0
    columns = _table_columns(conn, table)
    insert_columns = [column for column in columns if column != "id"]
    for row in rows:
        payload = {column: row.get(column) for column in insert_columns}
        if _row_exists(conn, table, row, MERGE_KEYS[table]):
            skipped += 1
            continue
        placeholders = ", ".join("?" for _ in payload)
        conn.execute(
            f"INSERT OR IGNORE INTO {table} ({', '.join(payload)}) VALUES ({placeholders})",  # noqa: S608
            tuple(payload.values()),
        )
        inserted += 1
    return inserted, skipped


def _table_columns(conn: sqlite3.Connection, table: str) -> list[str]:
    return [row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()]


def _row_exists(
    conn: sqlite3.Connection, table: str, row: dict[str, Any], keys: tuple[str, ...]
) -> bool:
    clauses: list[str] = []
    values: list[Any] = []
    for key in keys:
        if row.get(key) is None:
            clauses.append(f"{key} IS NULL")
        else:
            clauses.append(f"{key} = ?")
            values.append(row.get(key))
    existing = conn.execute(
        f"SELECT 1 FROM {table} WHERE {' AND '.join(clauses)} LIMIT 1",  # noqa: S608
        tuple(values),
    ).fetchone()
    return existing is not None


def _write_course_members(
    target_dir: Path,
    seed_courses: dict[str, Course],
    members: list[tuple[str, Course]],
    *,
    imported: list[str],
    skipped: list[str],
) -> None:
    target_dir.mkdir(parents=True, exist_ok=True)
    for _, course in members:
        if course.id in seed_courses:
            skipped.append(f"{course.id} (seed conflict)")
            continue
        export_course(course, target_dir / f"{course.id}.json")
        imported.append(course.id)
