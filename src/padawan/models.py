from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


Track = Literal["linux-bash", "git", "python", "k1s-workerbee"]
Level = Literal["basic", "intermediate", "advanced"]
RuntimeName = Literal["python", "bash", "git", "none"]


class GradingRule(BaseModel):
    kind: Literal["stdout_contains", "stderr_contains", "file_contains", "file_exists", "exit_code"]
    value: str | int | None = None
    path: str | None = None
    points: int = 1


class Lesson(BaseModel):
    id: str
    title: str
    concept_md: str
    prompt: str
    starter_code: str = ""
    language: str = "text"
    runtime: RuntimeName = "none"
    hidden_hint: str = ""
    grading: list[GradingRule] = Field(default_factory=list)
    codex_context: str = ""


class Module(BaseModel):
    id: str
    title: str
    summary: str = ""
    lessons: list[Lesson]


class BadgeDefinition(BaseModel):
    id: str
    title: str
    description: str
    criteria: dict[str, Any] = Field(default_factory=dict)
    issuer: dict[str, Any] = Field(default_factory=lambda: {"name": "Padawan Local"})
    share: dict[str, Any] = Field(default_factory=dict)


class Course(BaseModel):
    id: str
    title: str
    track: Track
    level: Level
    summary: str
    modules: list[Module]
    badges: list[BadgeDefinition] = Field(default_factory=list)
    generated: bool = False
    verified: bool = True

    @property
    def lessons(self) -> list[Lesson]:
        return [lesson for module in self.modules for lesson in module.lessons]

    @property
    def lesson_count(self) -> int:
        return len(self.lessons)


class CourseCard(BaseModel):
    id: str
    title: str
    track: str
    level: str
    summary: str
    completion_percent: int = 0
    completed_lessons: int = 0
    total_lessons: int = 0
    last_scored_at: str | None = None
    badges: list[dict[str, Any]] = Field(default_factory=list)
    generated: bool = False
    verified: bool = True


class RuntimeRequest(BaseModel):
    course_id: str
    lesson_id: str
    runtime: RuntimeName
    code: str


class RuntimeResult(BaseModel):
    status: Literal["passed", "failed", "error", "unavailable"]
    stdout: str = ""
    stderr: str = ""
    exit_code: int | None = None
    messages: list[str] = Field(default_factory=list)
    score_delta: int = 0


class CodexStatus(BaseModel):
    installed: bool
    authenticated: bool
    detail: str = ""


class GeneratedCourseRequest(BaseModel):
    prompt: str
    track: str | None = None
    level: str | None = None
