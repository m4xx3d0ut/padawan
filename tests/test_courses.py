from __future__ import annotations

from pathlib import Path

from padawan.courses import load_courses, validate_course_path
from padawan.settings import REPO_ROOT

CONTENT_DIR = REPO_ROOT / "content" / "courses"


def test_seed_courses_validate() -> None:
    assert validate_course_path(CONTENT_DIR) == []


def test_seed_courses_load_core_tracks() -> None:
    courses = load_courses(CONTENT_DIR)

    assert {"python-basics", "linux-bash-basics", "git-basics", "k1s-workerbee-concepts"} <= set(
        courses
    )
    assert courses["python-basics"].lesson_count == 4
    assert courses["k1s-workerbee-concepts"].lesson_count == 4
    assert courses["k1s-workerbee-concepts"].badges[0].criteria == {"completion_percent": 50}


def test_style_guide_declares_k1s_tokens() -> None:
    text = Path(REPO_ROOT / "docs" / "design" / "style-guide.md").read_text(encoding="utf-8")

    assert "#0f172a" in text
    assert "#2563eb" in text
    assert "WorkerBee" in text
