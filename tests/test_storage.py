from __future__ import annotations

from pathlib import Path

from padawan.courses import load_courses
from padawan.models import RuntimeResult
from padawan.settings import REPO_ROOT
from padawan.storage import Storage


def test_progress_and_badge_award(tmp_path: Path) -> None:
    storage = Storage(tmp_path / "state.sqlite3")
    course = load_courses(REPO_ROOT / "content" / "courses")["python-basics"]

    storage.record_attempt(
        course, course.lessons[0].id, RuntimeResult(status="passed", score_delta=1)
    )
    card = storage.course_card(course)
    assert card.completion_percent == 25
    assert card.badges == []

    storage.record_attempt(
        course, course.lessons[1].id, RuntimeResult(status="passed", score_delta=1)
    )
    card = storage.course_card(course)
    assert card.completion_percent == 50
    assert card.badges[0]["id"] == "python-basics-started"

    storage.record_attempt(
        course, course.lessons[2].id, RuntimeResult(status="passed", score_delta=1)
    )
    storage.record_attempt(
        course, course.lessons[3].id, RuntimeResult(status="passed", score_delta=1)
    )
    card = storage.course_card(course)
    assert card.completion_percent == 100
    assert {badge["id"] for badge in card.badges} == {
        "python-basics-started",
        "python-basics-complete",
    }


def test_course_cards_sort_by_latest_score(tmp_path: Path) -> None:
    storage = Storage(tmp_path / "state.sqlite3")
    courses = load_courses(REPO_ROOT / "content" / "courses")

    storage.record_attempt(
        courses["git-basics"],
        courses["git-basics"].lessons[0].id,
        RuntimeResult(status="passed", score_delta=1),
    )
    storage.record_attempt(
        courses["python-basics"],
        courses["python-basics"].lessons[0].id,
        RuntimeResult(status="passed", score_delta=1),
    )

    cards = storage.course_cards(courses.values())
    assert cards[0].id == "python-basics"


def test_validation_runs_and_codex_threads_are_persisted(tmp_path: Path) -> None:
    storage = Storage(tmp_path / "state.sqlite3")

    storage.record_validation_run("draft-python", "passed", '{"ok": true}')
    storage.upsert_codex_thread(
        thread_id="thread-1",
        course_id="python-basics",
        lesson_id="hello-python",
        title="Python Basics: Hello Python",
    )

    assert storage.latest_validation_for_course("draft-python")["status"] == "passed"
    thread = storage.codex_thread("thread-1")
    assert thread is not None
    assert thread["course_id"] == "python-basics"
