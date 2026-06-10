from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from .models import Course


class CourseLoadError(ValueError):
    pass


def load_course_file(path: Path) -> Course:
    try:
        return Course.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValidationError, ValueError) as exc:
        raise CourseLoadError(f"{path}: {exc}") from exc


def load_courses(content_dir: Path) -> dict[str, Course]:
    courses: dict[str, Course] = {}
    if not content_dir.exists():
        return courses
    for path in sorted(content_dir.glob("*.json")):
        course = load_course_file(path)
        courses[course.id] = course
    return courses


def load_course_dirs(*content_dirs: Path) -> dict[str, Course]:
    courses: dict[str, Course] = {}
    for content_dir in content_dirs:
        for course_id, course in load_courses(content_dir).items():
            courses.setdefault(course_id, course)
    return courses


def find_lesson(course: Course, lesson_id: str):
    for module in course.modules:
        for lesson in module.lessons:
            if lesson.id == lesson_id:
                return module, lesson
    raise KeyError(f"unknown lesson {lesson_id}")


def validate_course_path(path: Path) -> list[str]:
    errors: list[str] = []
    files = sorted(path.glob("*.json")) if path.is_dir() else [path]
    if not files:
        return [f"no course JSON files found at {path}"]
    seen: set[str] = set()
    for file_path in files:
        try:
            course = load_course_file(file_path)
        except CourseLoadError as exc:
            errors.append(str(exc))
            continue
        if course.id in seen:
            errors.append(f"duplicate course id {course.id}")
        seen.add(course.id)
        lesson_ids = [lesson.id for lesson in course.lessons]
        if len(lesson_ids) != len(set(lesson_ids)):
            errors.append(f"{course.id}: duplicate lesson id")
        if not course.lessons:
            errors.append(f"{course.id}: course has no lessons")
    return errors


def export_course(course: Course, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(course.model_dump(), indent=2, sort_keys=True)
    path.write_text(payload + "\n", encoding="utf-8")
