# Course Authoring

This page is for people creating or reviewing Padawan courses. You can write
courses by hand, generate drafts with Codex, or import local course files.

Seed courses are JSON files under `content/courses`. Local user courses live in
the Padawan state directory under `courses/`, and generated drafts live under
`course-drafts/`.

Each course contains modules, lessons, grading rules, optional badges, and hidden
validation metadata. Every publishable lesson should include a `reference_solution`
that passes local validation.

## Tracks And Levels

Supported tracks:

- `linux-bash`
- `git`
- `python`
- `webdev-ts-react`
- `webdev-python-htmx`
- `k1s-workerbee`
- `roblox`
- `unity`
- `unreal`

Supported levels:

- `basic`
- `intermediate`
- `advanced`

Use `basic` for first contact with a tool, `intermediate` for common workflows,
and `advanced` for recovery, automation, debugging, or architecture topics.

## Runtimes

Supported runtimes are `python`, `bash`, `git`, `node`, `text`, and `none`.
Roblox, Unity, and Unreal lessons use `text` validation until engine adapters are
available.

Choose the smallest runtime that proves the learning goal. For example, use
`text` for a conceptual Unreal lesson, `node` for a JavaScript exercise, and
`git` for repository workflow practice.

## Lesson Checklist

A good lesson has:

- a short title
- a focused prompt
- teaching material that explains one idea
- starter code that is close enough for a newcomer to begin
- a hidden hint that nudges without solving everything
- local grading rules
- a reference solution
- Codex context for explanations

Keep lessons small. A learner should understand what to try next after one read
of the prompt.

## Validation

Generated courses stay hidden until schema validation, badge checks, and reference
solution checks pass. Use the web Drafts page or the CLI:

```bash
padawan course validate --course all-seed
padawan course draft list
padawan course draft validate <course-id> --json
padawan course draft publish <course-id>
padawan course draft reject <course-id>
```

Validation is intentionally stricter than casual authoring. It protects learners
from broken generated material and keeps published courses recoverable through
backup/restore.

## Validation Status

The Drafts page shows the latest validation state for each generated course.
When JavaScript is enabled, pressing Validate queues a background run and the
card updates from `queued` to `running` to `passed` or `failed`.

Statuses mean:

- `queued`: Padawan accepted the validation request.
- `running`: validation is actively checking the draft.
- `passed`: the draft can be published.
- `failed`: at least one lesson, badge, runtime, or reference solution needs
  review.

For the MVP, the web app runs local validation directly. WorkerBee-backed
validation is still operator-driven, but the same status surface is ready to
show WorkerBee progress when that runner is attached.

## Badge Guidance

Seed courses use two local badges:

- 50 percent completion: started
- 100 percent completion: complete

Future cloud sharing can use the existing stable badge IDs, issuer metadata, and
share placeholder fields. Do not reuse badge IDs for different achievements.

## Reviewing Generated Drafts

Before publishing a generated draft:

1. Open the Drafts page.
2. Run validation.
3. Read the course title, summary, lessons, hints, and grading messages.
4. Confirm that the reference solutions are appropriate for the skill level.
5. Publish only after the course is clear and validation passes.

Reject drafts that are too broad, too vague, unsafe, or outside the available
runtime support.
