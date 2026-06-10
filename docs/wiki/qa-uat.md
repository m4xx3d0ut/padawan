# QA and UAT

Use this path for interactive QA:

```bash
ruff format --check
ruff check
pytest
padawan course validate --course all-seed
padawan data export --output /tmp/padawan-backup.zip
padawan data inspect /tmp/padawan-backup.zip
padawan serve
```

Manual checks:

- Landing page renders the prompt and course cards.
- Course cards show progress and badges.
- Lesson page uses a left teaching pane and right editor/runtime pane.
- Hint reveal works.
- Python, Bash, Git, and k1s seed lessons can be run.
- `/data` exports a backup and imports it with a safe merge summary.
- Codex status is visible and explain requests fail clearly when Codex is not
  available.
- `/docs` exposes the local wiki.
