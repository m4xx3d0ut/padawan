# Badges

Badges are local-first records. Each badge has a stable ID, title, description,
criteria, issuer metadata, and a placeholder share object for future cloud
sharing.

The MVP awards local badges when a course reaches the configured completion
percentage. Seed courses include a 50 percent started badge and a 100 percent
completion badge.

## What Learners See

Course cards show whether badges have been earned. A badge is local to the
current Padawan data directory unless future sharing features are added.

## Authoring Rules

- Use stable badge IDs.
- Keep titles short.
- Write descriptions that explain the achievement in plain language.
- Use completion criteria that can be computed from local progress.
- Keep issuer metadata present, even for local-only badges.
- Leave the share object available for future cloud/profile features.

## Backup Behavior

Badge awards are included in Padawan backups. Restoring a backup imports missing
badge awards with the rest of the learner's progress.
