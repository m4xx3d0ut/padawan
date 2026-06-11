from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

TRAINING_DATA_FORMAT = "padawan.training-data.v1"
LEGACY_TRAINING_DATA_FORMAT = "padawan.training-data.legacy"
TRAINING_DATA_SCHEMA_ID = "https://padawan.local/schemas/padawan-training-data-v1.schema.json"


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


Track = Literal[
    "linux-bash",
    "git",
    "python",
    "webdev-ts-react",
    "webdev-python-htmx",
    "k1s-workerbee",
    "roblox",
    "unity",
    "unreal",
]
Level = Literal["basic", "intermediate", "advanced"]
RuntimeName = Literal["python", "bash", "git", "node", "text", "none"]
Visibility = Literal["local", "unlisted", "public"]
ExerciseDifficulty = Literal["practice", "challenge", "review"]


class GradingRule(BaseModel):
    kind: Literal[
        "stdout_contains",
        "stderr_contains",
        "file_contains",
        "file_exists",
        "exit_code",
        "text_contains",
    ]
    value: str | int | None = None
    path: str | None = None
    points: int = 1


class ConceptLink(BaseModel):
    title: str
    url: str
    description: str = ""


class PersonRef(BaseModel):
    name: str
    url: str = ""
    email: str = ""


class LicenseInfo(BaseModel):
    id: str = "Apache-2.0"
    name: str = "Apache License 2.0"
    url: str = "https://www.apache.org/licenses/LICENSE-2.0"


class CourseShareMetadata(BaseModel):
    visibility: Visibility = "local"
    slug: str = ""
    canonical_url: str = ""
    repository_url: str = ""


class CourseProvenance(BaseModel):
    source: str = "padawan"
    generated_by: str = ""
    prompt: str = ""
    reviewed_by: list[PersonRef] = Field(default_factory=list)


class TrainingExample(BaseModel):
    title: str
    explanation: str
    code: str = ""
    output: str = ""
    docs: list[ConceptLink] = Field(default_factory=list)


class LessonExercise(BaseModel):
    id: str
    title: str
    prompt: str
    difficulty: ExerciseDifficulty = "practice"
    starter_code: str = ""
    hidden_hint: str = ""
    reference_solution: str = ""
    grading: list[GradingRule] = Field(default_factory=list)


class Lesson(BaseModel):
    id: str
    title: str
    concept_md: str
    concept_summary: str = ""
    concept_links: list[ConceptLink] = Field(default_factory=list)
    examples: list[TrainingExample] = Field(default_factory=list)
    exercises: list[LessonExercise] = Field(default_factory=list)
    prompt: str
    starter_code: str = ""
    language: str = "text"
    runtime: RuntimeName = "none"
    hidden_hint: str = ""
    grading: list[GradingRule] = Field(default_factory=list)
    codex_context: str = ""
    reference_solution: str = ""
    toolchain: dict[str, Any] = Field(default_factory=dict)


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
    schema_version: str = LEGACY_TRAINING_DATA_FORMAT
    content_version: str = "0.1.0"
    id: str
    title: str
    track: Track
    level: Level
    summary: str
    author: PersonRef = Field(default_factory=lambda: PersonRef(name="Padawan contributors"))
    maintainers: list[PersonRef] = Field(default_factory=list)
    license: LicenseInfo = Field(default_factory=LicenseInfo)
    tags: list[str] = Field(default_factory=list)
    prerequisites: list[str] = Field(default_factory=list)
    learning_objectives: list[str] = Field(default_factory=list)
    target_audience: str = ""
    estimated_minutes: int = 0
    provenance: CourseProvenance = Field(default_factory=CourseProvenance)
    share: CourseShareMetadata = Field(default_factory=CourseShareMetadata)
    created_at: str = ""
    updated_at: str = ""
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


def training_data_json_schema() -> dict[str, Any]:
    schema = Course.model_json_schema()
    schema["$id"] = TRAINING_DATA_SCHEMA_ID
    schema["title"] = "Padawan Training Data v1"
    return schema


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


class CourseValidationResult(BaseModel):
    course_id: str | None = None
    status: Literal["passed", "failed"] = "failed"
    messages: list[str] = Field(default_factory=list)
    runnable_lessons: int = 0
    skipped_lessons: int = 0
