# Data Backup And Restore

Padawan stores learner data locally in the configured state directory.

Use the web UI at `/data` or the CLI:

```bash
padawan data export --output padawan-backup.zip
padawan data inspect padawan-backup.zip
padawan data import padawan-backup.zip --dry-run
padawan data import padawan-backup.zip
```

Backups are zip archives that include progress attempts, progress events, badge
awards, generation jobs, validation runs, local published courses, and local
course drafts.

Restores use a safe merge. Padawan creates a pre-restore backup, inserts missing
records, imports valid local course files, and skips course IDs that conflict
with seed courses.

Backups do not include Codex authentication, environment variables, temporary
runtime workspaces, or WorkerBee credentials.
