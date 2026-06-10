# Course Authoring

Seed courses are JSON files under `content/courses`. Local user courses live in
the Padawan state directory under `courses/`, and generated drafts live under
`course-drafts/`.

Each course contains modules, lessons, grading rules, and optional badges.
Generated courses should stay hidden until schema validation and reference
solution checks pass.

Run:

```bash
padawan course validate --course all-seed
```
