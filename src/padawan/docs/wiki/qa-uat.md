# QA and UAT

Use this path for interactive QA:

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

Manual checks:

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
