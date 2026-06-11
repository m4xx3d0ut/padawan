from __future__ import annotations

from padawan.codex import COURSE_GENERATION_PROFILE, COURSE_SCHEMA
from padawan.models import TRAINING_DATA_FORMAT, TRAINING_DATA_SCHEMA_ID


def test_codex_generation_profile_targets_training_data_v1() -> None:
    profile = COURSE_GENERATION_PROFILE.read_text(encoding="utf-8")

    assert COURSE_SCHEMA["$id"] == TRAINING_DATA_SCHEMA_ID
    assert "examples" in COURSE_SCHEMA["$defs"]["Lesson"]["properties"]
    assert "exercises" in COURSE_SCHEMA["$defs"]["Lesson"]["properties"]
    assert TRAINING_DATA_FORMAT in profile
    assert "concept_links" in profile
    assert "reference_solution" in profile
