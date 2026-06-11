from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from .models import Course, CourseValidationResult
from .settings import Settings


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


def validate_course_for_publish(
    course: Course,
    settings: Settings,
    *,
    existing_course_ids: set[str] | None = None,
) -> CourseValidationResult:
    messages = _validate_course_shape(course, existing_course_ids=existing_course_ids)
    runnable_lessons = 0
    skipped_lessons = 0

    from .runtime import run_lesson

    for lesson in course.lessons:
        if lesson.runtime == "none":
            skipped_lessons += 1
            continue
        runnable_lessons += 1
        reference = lesson.reference_solution or lesson.starter_code
        if not reference.strip():
            messages.append(f"{course.id}/{lesson.id}: missing reference_solution")
            continue
        result = run_lesson(lesson, reference, settings)
        if result.status != "passed":
            messages.append(
                f"{course.id}/{lesson.id}: reference validation {result.status}: "
                + "; ".join(result.messages)
            )

    return CourseValidationResult(
        course_id=course.id,
        status="failed" if messages else "passed",
        messages=messages,
        runnable_lessons=runnable_lessons,
        skipped_lessons=skipped_lessons,
    )


def _validate_course_shape(
    course: Course,
    *,
    existing_course_ids: set[str] | None = None,
) -> list[str]:
    messages: list[str] = []
    if existing_course_ids and course.id in existing_course_ids:
        messages.append(f"{course.id}: course id already exists")
    if not course.lessons:
        messages.append(f"{course.id}: course has no lessons")
    lesson_ids = [lesson.id for lesson in course.lessons]
    if len(lesson_ids) != len(set(lesson_ids)):
        messages.append(f"{course.id}: duplicate lesson id")
    for lesson in course.lessons:
        if not lesson.hidden_hint.strip():
            messages.append(f"{course.id}/{lesson.id}: missing hidden_hint")
        if lesson.runtime != "none" and not lesson.grading:
            messages.append(f"{course.id}/{lesson.id}: missing grading rules")
    badge_thresholds = {
        int(badge.criteria.get("completion_percent", 0))
        for badge in course.badges
        if "completion_percent" in badge.criteria
    }
    if 50 not in badge_thresholds:
        messages.append(f"{course.id}: missing 50 percent badge")
    if 100 not in badge_thresholds:
        messages.append(f"{course.id}: missing 100 percent badge")
    return messages


def draft_path(draft_dir: Path, course_id: str) -> Path:
    return draft_dir / f"{course_id}.json"


def load_drafts(draft_dir: Path) -> dict[str, Course]:
    return load_courses(draft_dir)


def publish_draft(
    settings: Settings,
    course_id: str,
    *,
    existing_course_ids: set[str] | None = None,
) -> CourseValidationResult:
    source = draft_path(settings.course_draft_dir, course_id)
    course = load_course_file(source)
    result = validate_course_for_publish(
        course,
        settings,
        existing_course_ids=existing_course_ids,
    )
    if result.status != "passed":
        return result
    published = course.model_copy(update={"verified": True})
    export_course(published, settings.user_course_dir / f"{published.id}.json")
    source.unlink()
    return result


def reject_draft(settings: Settings, course_id: str) -> None:
    draft_path(settings.course_draft_dir, course_id).unlink()


def export_course(course: Course, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(course.model_dump(), indent=2, sort_keys=True)
    path.write_text(payload + "\n", encoding="utf-8")
