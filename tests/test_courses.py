from __future__ import annotations

from pathlib import Path

from padawan.courses import load_courses, validate_course_for_publish, validate_course_path
from padawan.settings import REPO_ROOT, Settings

CONTENT_DIR = REPO_ROOT / "content" / "courses"


def test_seed_courses_validate() -> None:
    assert validate_course_path(CONTENT_DIR) == []


def test_seed_courses_load_core_tracks() -> None:
    courses = load_courses(CONTENT_DIR)

    assert {"python-basics", "linux-bash-basics", "git-basics", "k1s-workerbee-concepts"} <= set(
        courses
    )
    assert len(courses) == 27
    assert courses["python-basics"].lesson_count == 4
    assert courses["k1s-workerbee-concepts"].lesson_count == 4
    assert courses["k1s-workerbee-concepts"].badges[0].criteria == {"completion_percent": 50}


def test_seed_catalog_covers_requested_tracks_and_levels(tmp_path: Path) -> None:
    settings = Settings(
        state_dir=tmp_path,
        content_dir=CONTENT_DIR,
        docs_dir=REPO_ROOT / "docs" / "wiki",
    )
    courses = load_courses(CONTENT_DIR)

    expected_tracks = {
        "linux-bash",
        "git",
        "python",
        "webdev-ts-react",
        "webdev-python-htmx",
        "k1s-workerbee",
        "roblox",
        "unity",
        "unreal",
    }
    assert {course.track for course in courses.values()} == expected_tracks
    for track in expected_tracks:
        assert {course.level for course in courses.values() if course.track == track} == {
            "basic",
            "intermediate",
            "advanced",
        }

    for course in courses.values():
        result = validate_course_for_publish(course, settings)
        assert result.status == "passed", result.messages
        for lesson in course.lessons:
            assert lesson.hidden_hint
            assert lesson.reference_solution


def test_style_guide_declares_k1s_tokens() -> None:
    text = Path(REPO_ROOT / "docs" / "design" / "style-guide.md").read_text(encoding="utf-8")

    assert "#0f172a" in text
    assert "#2563eb" in text
    assert "WorkerBee" in text
