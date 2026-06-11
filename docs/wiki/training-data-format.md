# Training Data Format

Padawan course files use the `padawan.training-data.v1` format. The format is
local-first today, but includes metadata that can support publishing, sharing,
profiles, and badge portability later.

The exported JSON Schema is tracked at:

```text
docs/schemas/padawan-training-data-v1.schema.json
```

## Course Metadata

Every v1 course should include:

- `schema_version`: `padawan.training-data.v1`
- `content_version`: version of this course content
- `author` and optional `maintainers`
- `license`
- `tags`
- `prerequisites`
- `learning_objectives`
- `target_audience`
- `estimated_minutes`
- `provenance`
- `share`
- `badges`

The `share` object is intentionally small for now. Use `visibility`, `slug`,
`canonical_url`, and `repository_url` so future cloud features can attach to the
same data without rewriting local courses.

## Lesson Content

Every v1 lesson should include:

- `concept_md`: short teaching material rendered in the lesson pane
- `concept_summary`: two to four newcomer-friendly sentences
- `concept_links`: one to four relevant project documentation links
- `examples`: worked examples with explanation, code or text, expected output
  when useful, and optional docs links
- the primary exercise fields: `prompt`, `starter_code`, `runtime`, `grading`,
  `hidden_hint`, and `reference_solution`
- `exercises`: follow-up practice items or challenges
- `codex_context`
- `toolchain`

Keep the primary exercise small. Follow-up `exercises` are for extra practice,
not a replacement for the runnable editor task.

## Compatibility

Older local courses without `schema_version` can still load as legacy content.
Bundled courses and newly generated drafts should use v1. Generated drafts must
validate as v1 before publishing.

## Codex Generation

Padawan uses a versioned prompt profile for course generation:

```text
src/padawan/prompt_profiles/course_generation_v1.md
```

The prompt profile requests the v1 schema, official docs links, examples,
follow-up exercises, stable badges, and validation-friendly reference solutions.
This profile can later be promoted into a dedicated Codex skill.

## Validation Expectations

Validation checks:

- v1 course metadata is present
- lesson IDs are unique
- each v1 lesson has concept links, examples, and follow-up exercises
- hidden hints are present
- runnable lessons have grading rules and reference solutions
- reference solutions pass local runtime validation
- courses include 50 percent and 100 percent completion badges

Use:

```bash
padawan course validate --course all-seed
padawan course draft validate <course-id> --json
```
