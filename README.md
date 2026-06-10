# Padawan

Padawan is a local progressive coding teacher. It serves a small web UI, stores learner
progress locally, runs beginner exercises in controlled temporary workspaces, and uses the
user's existing Codex CLI login for generated explanations and course drafts.

## Quickstart

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e .[dev]
padawan doctor
padawan serve
```

Open `http://127.0.0.1:8787/`.

## Codex

Padawan calls the installed `codex` CLI. It does not read or store Codex auth files.
Run this once if Codex is not already signed in:

```bash
codex login
```

## Checks

```bash
ruff format --check
ruff check
pytest
padawan course validate --course all-seed
padawan data export --output /tmp/padawan-backup.zip
padawan data inspect /tmp/padawan-backup.zip
```

## Data

Use the `/data` page or `padawan data` commands to back up and restore local
progress, badges, generated drafts, and local courses. Restore uses a safe merge
and creates a pre-restore backup before writing.

## WorkerBee

WorkerBee is optional for novice seed-course use, but it is the validation workbench for
publishable generated courses and deployable app checks.
