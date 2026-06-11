from __future__ import annotations

from pathlib import Path

from padawan.courses import load_courses
from padawan.runtime import run_lesson
from padawan.settings import REPO_ROOT, Settings


def test_python_lesson_passes_with_expected_output(tmp_path: Path) -> None:
    settings = Settings(state_dir=tmp_path)
    course = load_courses(REPO_ROOT / "content" / "courses")["python-basics"]
    lesson = course.lessons[0]

    result = run_lesson(lesson, "print('Hello, Padawan!')", settings)

    assert result.status == "passed"
    assert result.score_delta == 2


def test_python_lesson_fails_when_output_missing(tmp_path: Path) -> None:
    settings = Settings(state_dir=tmp_path)
    course = load_courses(REPO_ROOT / "content" / "courses")["python-basics"]
    lesson = course.lessons[0]

    result = run_lesson(lesson, "print('nope')", settings)

    assert result.status == "failed"
    assert any("stdout_contains" in message for message in result.messages)


def test_node_lesson_passes_with_expected_output(tmp_path: Path) -> None:
    settings = Settings(state_dir=tmp_path)
    course = load_courses(REPO_ROOT / "content" / "courses")["webdev-ts-react-basic"]
    lesson = course.lessons[0]

    result = run_lesson(lesson, lesson.reference_solution, settings)

    assert result.status == "passed"


def test_text_lesson_grades_answer_text(tmp_path: Path) -> None:
    settings = Settings(state_dir=tmp_path)
    course = load_courses(REPO_ROOT / "content" / "courses")["unity-basic"]
    lesson = course.lessons[0]

    result = run_lesson(lesson, lesson.reference_solution, settings)

    assert result.status == "passed"
    assert result.exit_code == 0
