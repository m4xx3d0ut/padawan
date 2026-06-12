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

    run_id = storage.record_validation_run("draft-python", "running", "Queued")
    storage.set_validation_run(run_id, "passed", '{"ok": true}')
    storage.upsert_codex_thread(
        thread_id="thread-1",
        course_id="python-basics",
        lesson_id="hello-python",
        title="Python Basics: Hello Python",
    )

    assert storage.latest_validation_for_course("draft-python")["status"] == "passed"
    assert storage.validation_run(run_id)["status"] == "passed"
    thread = storage.codex_thread("thread-1")
    assert thread is not None
    assert thread["course_id"] == "python-basics"


def test_peer_identity_course_inbox_and_progress(tmp_path: Path) -> None:
    storage = Storage(tmp_path / "state.sqlite3")
    course = load_courses(REPO_ROOT / "content" / "courses")["python-basics"]

    identity = storage.peer_identity("Ahsoka", "padawan")
    same_identity = storage.peer_identity(" Ahsoka ", "padawan")
    inbox_id = storage.record_peer_course(
        peer_id=identity.peer_id,
        course_id=course.id,
        course_payload=course.model_dump(),
    )
    storage.upsert_peer_progress(
        peer_id=identity.peer_id,
        course_id=course.id,
        payload={"completed_lessons": ["hello-python"]},
    )

    assert identity.peer_id == same_identity.peer_id
    assert inbox_id == 1
    assert storage.peer_courses(identity.peer_id)[0]["course"]["id"] == "python-basics"
    assert storage.peer_progress(identity.peer_id)[0]["payload"] == {
        "completed_lessons": ["hello-python"]
    }
