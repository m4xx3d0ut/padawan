# Data Backup And Restore

Padawan stores learner data locally in the configured state directory. Backups
are the easiest way to move that data to another machine or protect it before
testing new course drafts.

Use the web UI at `/data` for the simplest flow, or use the CLI:

```bash
padawan data export --output padawan-backup.zip
padawan data inspect padawan-backup.zip
padawan data import padawan-backup.zip --dry-run
padawan data import padawan-backup.zip
```

Always run `inspect` or `--dry-run` before a real import when the backup came
from another machine.

## What Is Included

Backups are zip archives that include progress attempts, progress events, badge
awards, generation jobs, validation runs, local published courses, and local
course drafts.

Codex thread metadata is included so lesson conversations can be listed locally,
but Codex credentials are not included.

## What Is Not Included

Backups do not include:

- Codex authentication files
- API keys or access tokens
- environment variables
- temporary runtime workspaces
- WorkerBee credentials
- installed Python, Node, Git, Bash, or engine runtimes

## Restore Behavior

Restores use a safe merge. Padawan creates a pre-restore backup, inserts missing
records, imports valid local course files, and skips course IDs that conflict
with seed courses.

Safe merge means restore should not erase existing local progress. If a record
already exists, Padawan keeps the existing record and imports only missing data.

## Good Backup Habits

- Export a backup before importing another backup.
- Export a backup before publishing generated courses during UAT.
- Keep at least one backup outside the repo checkout.
- Name backups with a date when sharing them with testers.

Example:

```bash
padawan data export --output padawan-backup-2026-06-11.zip
```

## If Import Fails

Do not repeatedly import the same file without reading the error. First inspect
the archive:

```bash
padawan data inspect padawan-backup.zip
```

Then try a dry run:

```bash
padawan data import padawan-backup.zip --dry-run
```

If the backup contains course files that conflict with bundled seed courses,
Padawan skips those local course files by design.
