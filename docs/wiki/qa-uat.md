# QA and UAT

Use this path for interactive QA. It is written for testers who may not know the
internals of Padawan.

## Before You Start

Confirm the app installs and the seed catalog validates:

```bash
ruff format --check
ruff check
pytest
padawan course validate --course all-seed
padawan course draft list
padawan data export --output /tmp/padawan-backup.zip
padawan data inspect /tmp/padawan-backup.zip
padawan serve
```

Open `http://127.0.0.1:8787/`.

## Manual Checks

- Landing page renders the prompt and course cards.
- Course cards show progress and badges.
- Course filters narrow by track and level.
- Lesson page uses a left teaching pane and right editor/runtime pane.
- Hint reveal works.
- Python, Bash, Git, Node, and text seed lessons can be run.
- `/drafts` shows generated course drafts and supports validate, publish, and
  reject actions.
- `/data` exports a backup and imports it with a safe merge summary.
- Codex status is visible and explain requests fail clearly when Codex is not
  available.
- Codex explanations can continue in the same thread when Codex returns a thread id.
- `/docs` exposes the local wiki.
- WorkerBee deploys the image, probes `/healthz`, `/courses`, `/docs`, `/data`,
  `/runtime/run`, and `/data/export`, and confirms `/data/padawan` is writable.

## Newcomer UAT Path

Ask a tester to complete this without coaching:

1. Install Padawan from the README.
2. Open the app.
3. Find Python Basics.
4. Run the first lesson once without changing code.
5. Read the feedback.
6. Fix the starter code and pass the lesson.
7. Reveal a hint on another lesson.
8. Export a backup.
9. Open the docs page and find troubleshooting guidance.

If they cannot complete a step, improve the UI text or docs before adding more
features.

## Generated Course UAT Path

1. Sign in to Codex.
2. Generate a small course request, such as "basic Bash loops".
3. Confirm the generated course appears in Drafts, not Courses.
4. Validate the draft.
5. Publish only if validation passes.
6. Open the course and run at least one lesson.
7. Export a backup and inspect it.

## Evidence To Capture

For each QA pass, record:

- operating system
- Python version
- browser
- install command used
- failing route or command
- screenshot or terminal output for failures
- whether the issue affects bundled courses, generated courses, Codex, backup,
  or WorkerBee deployment
