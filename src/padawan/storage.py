from __future__ import annotations

import json
import secrets
import sqlite3
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from .models import Course, CourseCard, RuntimeResult, utc_now_iso
from .peer import PeerIdentity, PeerRole, normalize_username, peer_id, peer_suffix

SCHEMA = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id TEXT NOT NULL,
    lesson_id TEXT NOT NULL,
    status TEXT NOT NULL,
    score_delta INTEGER NOT NULL DEFAULT 0,
    stdout TEXT NOT NULL DEFAULT '',
    stderr TEXT NOT NULL DEFAULT '',
    messages_json TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS progress_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id TEXT NOT NULL,
    lesson_id TEXT,
    event_type TEXT NOT NULL,
    payload_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS badge_awards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id TEXT NOT NULL,
    badge_id TEXT NOT NULL,
    payload_json TEXT NOT NULL DEFAULT '{}',
    awarded_at TEXT NOT NULL,
    UNIQUE(course_id, badge_id)
);
CREATE TABLE IF NOT EXISTS generation_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prompt TEXT NOT NULL,
    status TEXT NOT NULL,
    course_id TEXT,
    detail TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS validation_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id TEXT,
    status TEXT NOT NULL,
    detail TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS codex_threads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    thread_id TEXT NOT NULL UNIQUE,
    course_id TEXT NOT NULL,
    lesson_id TEXT NOT NULL,
    title TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS peer_local_state (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS peer_identities (
    peer_id TEXT PRIMARY KEY,
    username TEXT NOT NULL,
    role TEXT NOT NULL,
    suffix TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS peer_course_inbox (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    peer_id TEXT NOT NULL,
    course_id TEXT NOT NULL,
    course_json TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'received',
    received_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS peer_progress_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    peer_id TEXT NOT NULL,
    course_id TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(peer_id, course_id)
);
"""


class Storage:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init(self) -> None:
        with self.connect() as conn:
            conn.executescript(SCHEMA)

    def record_attempt(self, course: Course, lesson_id: str, result: RuntimeResult) -> None:
        now = utc_now_iso()
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO attempts
                    (
                        course_id, lesson_id, status, score_delta,
                        stdout, stderr, messages_json, created_at
                    )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    course.id,
                    lesson_id,
                    result.status,
                    result.score_delta,
                    result.stdout,
                    result.stderr,
                    json.dumps(result.messages),
                    now,
                ),
            )
            conn.execute(
                """
                INSERT INTO progress_events
                    (course_id, lesson_id, event_type, payload_json, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    course.id,
                    lesson_id,
                    "attempt_scored",
                    json.dumps({"status": result.status, "score_delta": result.score_delta}),
                    now,
                ),
            )
        if result.status == "passed":
            self._maybe_award_badges(course)

    def latest_attempts(self, course_id: str) -> dict[str, sqlite3.Row]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT a.*
                FROM attempts a
                JOIN (
                    SELECT lesson_id, MAX(id) AS max_id
                    FROM attempts
                    WHERE course_id = ?
                    GROUP BY lesson_id
                ) latest ON latest.max_id = a.id
                """,
                (course_id,),
            ).fetchall()
        return {row["lesson_id"]: row for row in rows}

    def course_cards(self, courses: Iterable[Course]) -> list[CourseCard]:
        cards = [self.course_card(course) for course in courses]
        return sorted(
            cards,
            key=lambda card: card.last_scored_at or "",
            reverse=True,
        )

    def course_card(self, course: Course) -> CourseCard:
        attempts = self.latest_attempts(course.id)
        completed = sum(1 for row in attempts.values() if row["status"] == "passed")
        total = course.lesson_count
        completion = int((completed / total) * 100) if total else 0
        latest = self.latest_scored_at(course.id)
        return CourseCard(
            id=course.id,
            title=course.title,
            track=course.track,
            level=course.level,
            summary=course.summary,
            completion_percent=completion,
            completed_lessons=completed,
            total_lessons=total,
            last_scored_at=latest,
            badges=self.badges_for_course(course.id),
            generated=course.generated,
            verified=course.verified,
        )

    def lesson_status(self, course_id: str, lesson_id: str) -> str:
        row = self.latest_attempts(course_id).get(lesson_id)
        return row["status"] if row else "not-started"

    def latest_scored_at(self, course_id: str) -> str | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT MAX(created_at) AS latest FROM attempts WHERE course_id = ?",
                (course_id,),
            ).fetchone()
        return row["latest"] if row and row["latest"] else None

    def badges_for_course(self, course_id: str) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT badge_id, payload_json, awarded_at FROM badge_awards WHERE course_id = ?",
                (course_id,),
            ).fetchall()
        return [
            {
                "id": row["badge_id"],
                "awarded_at": row["awarded_at"],
                "payload": json.loads(row["payload_json"]),
            }
            for row in rows
        ]

    def _maybe_award_badges(self, course: Course) -> None:
        card = self.course_card(course)
        now = utc_now_iso()
        with self.connect() as conn:
            for badge in course.badges:
                requires = int(badge.criteria.get("completion_percent", 100))
                if card.completion_percent < requires:
                    continue
                conn.execute(
                    """
                    INSERT OR IGNORE INTO badge_awards
                        (course_id, badge_id, payload_json, awarded_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        course.id,
                        badge.id,
                        json.dumps(badge.model_dump()),
                        now,
                    ),
                )

    def create_generation_job(self, prompt: str) -> int:
        now = utc_now_iso()
        with self.connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO generation_jobs (prompt, status, created_at, updated_at)
                VALUES (?, 'queued', ?, ?)
                """,
                (prompt, now, now),
            )
            return int(cur.lastrowid)

    def set_generation_job(
        self, job_id: int, *, status: str, detail: str = "", course_id: str | None = None
    ) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE generation_jobs
                SET status = ?, detail = ?, course_id = COALESCE(?, course_id), updated_at = ?
                WHERE id = ?
                """,
                (status, detail, course_id, utc_now_iso(), job_id),
            )

    def generation_job(self, job_id: int) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM generation_jobs WHERE id = ?", (job_id,)).fetchone()
        return dict(row) if row else None

    def record_validation_run(self, course_id: str | None, status: str, detail: str) -> int:
        return self.create_validation_run(course_id, status, detail)

    def create_validation_run(self, course_id: str | None, status: str, detail: str) -> int:
        with self.connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO validation_runs (course_id, status, detail, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (course_id, status, detail, utc_now_iso()),
            )
            return int(cur.lastrowid)

    def set_validation_run(self, run_id: int, status: str, detail: str) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE validation_runs
                SET status = ?, detail = ?
                WHERE id = ?
                """,
                (status, detail, run_id),
            )

    def validation_run(self, run_id: int) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM validation_runs WHERE id = ?", (run_id,)).fetchone()
        return dict(row) if row else None

    def latest_validation_for_course(self, course_id: str) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT *
                FROM validation_runs
                WHERE course_id = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (course_id,),
            ).fetchone()
        return dict(row) if row else None

    def upsert_codex_thread(
        self,
        *,
        thread_id: str,
        course_id: str,
        lesson_id: str,
        title: str = "",
    ) -> None:
        now = utc_now_iso()
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO codex_threads
                    (thread_id, course_id, lesson_id, title, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(thread_id) DO UPDATE SET
                    course_id = excluded.course_id,
                    lesson_id = excluded.lesson_id,
                    title = excluded.title,
                    updated_at = excluded.updated_at
                """,
                (thread_id, course_id, lesson_id, title, now, now),
            )

    def codex_thread(self, thread_id: str) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM codex_threads WHERE thread_id = ?",
                (thread_id,),
            ).fetchone()
        return dict(row) if row else None

    def peer_local_seed(self) -> str:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT value FROM peer_local_state WHERE key = 'identity_seed'"
            ).fetchone()
            if row:
                return str(row["value"])
            seed = secrets.token_hex(16)
            conn.execute(
                "INSERT INTO peer_local_state (key, value) VALUES ('identity_seed', ?)",
                (seed,),
            )
        return seed

    def peer_identity(self, username: str, role: PeerRole) -> PeerIdentity:
        seed = self.peer_local_seed()
        normalized = normalize_username(username)
        suffix = peer_suffix(normalized, role, seed)
        identity = PeerIdentity(
            peer_id=peer_id(normalized, role, seed),
            username=normalized,
            role=role,
            suffix=suffix,
        )
        self.upsert_peer_identity(identity)
        return identity

    def upsert_peer_identity(self, identity: PeerIdentity) -> None:
        now = utc_now_iso()
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO peer_identities
                    (peer_id, username, role, suffix, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(peer_id) DO UPDATE SET
                    username = excluded.username,
                    role = excluded.role,
                    suffix = excluded.suffix,
                    updated_at = excluded.updated_at
                """,
                (
                    identity.peer_id,
                    identity.username,
                    identity.role,
                    identity.suffix,
                    now,
                    now,
                ),
            )

    def peer_identities(self) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT peer_id, username, role, suffix, created_at, updated_at
                FROM peer_identities
                ORDER BY updated_at DESC, username
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def record_peer_course(
        self,
        *,
        peer_id: str,
        course_id: str,
        course_payload: dict[str, Any],
        status: str = "received",
    ) -> int:
        with self.connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO peer_course_inbox
                    (peer_id, course_id, course_json, status, received_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    peer_id,
                    course_id,
                    json.dumps(course_payload, sort_keys=True),
                    status,
                    utc_now_iso(),
                ),
            )
            return int(cur.lastrowid)

    def peer_courses(self, peer_id: str | None = None) -> list[dict[str, Any]]:
        sql = """
            SELECT id, peer_id, course_id, course_json, status, received_at
            FROM peer_course_inbox
        """
        params: tuple[Any, ...] = ()
        if peer_id:
            sql += " WHERE peer_id = ?"
            params = (peer_id,)
        sql += " ORDER BY id DESC"
        with self.connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        items = []
        for row in rows:
            item = dict(row)
            item["course"] = json.loads(item.pop("course_json"))
            items.append(item)
        return items

    def upsert_peer_progress(
        self, *, peer_id: str, course_id: str, payload: dict[str, Any]
    ) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO peer_progress_snapshots
                    (peer_id, course_id, payload_json, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(peer_id, course_id) DO UPDATE SET
                    payload_json = excluded.payload_json,
                    updated_at = excluded.updated_at
                """,
                (peer_id, course_id, json.dumps(payload, sort_keys=True), utc_now_iso()),
            )

    def peer_progress(self, peer_id: str | None = None) -> list[dict[str, Any]]:
        sql = """
            SELECT id, peer_id, course_id, payload_json, updated_at
            FROM peer_progress_snapshots
        """
        params: tuple[Any, ...] = ()
        if peer_id:
            sql += " WHERE peer_id = ?"
            params = (peer_id,)
        sql += " ORDER BY updated_at DESC"
        with self.connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        items = []
        for row in rows:
            item = dict(row)
            item["payload"] = json.loads(item.pop("payload_json"))
            items.append(item)
        return items

    def local_progress_payload(self, course_id: str) -> dict[str, Any]:
        attempts = self.latest_attempts(course_id)
        return {
            "course_id": course_id,
            "lessons": {
                lesson_id: {
                    "status": row["status"],
                    "score_delta": row["score_delta"],
                    "created_at": row["created_at"],
                }
                for lesson_id, row in attempts.items()
            },
            "badges": self.badges_for_course(course_id),
            "last_scored_at": self.latest_scored_at(course_id),
        }
