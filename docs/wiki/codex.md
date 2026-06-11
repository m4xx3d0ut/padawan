# Codex Integration

Padawan uses the installed Codex CLI as the local ChatGPT/Codex bridge.

Codex is optional. The bundled catalog, progress tracking, badges, local docs,
and backups all work without it.

## Setup

```bash
codex login
padawan codex status
```

If `padawan codex status` reports that Codex is unavailable, install or sign in
to the Codex CLI first, then restart Padawan.

## What Padawan Sends

Padawan sends the lesson prompt, relevant course context, and your request for
help. For generated courses, it sends the topic you asked to learn and requests
a structured course draft.

Padawan does not read or store `~/.codex/auth.json`. It calls `codex exec
--json` for generated explanations and course drafts, using your existing Codex
CLI session.

When Codex returns a thread id, Padawan stores lightweight local metadata for the
course and lesson. Follow-up messages use `codex exec resume <thread-id> --json`
so the lesson dialog can continue the same tutoring thread.

Padawan never stores Codex auth files, API keys, or access tokens.

## Good Ways To Ask

Use Codex to improve understanding:

- "Explain why my loop stops early."
- "Give me a smaller hint, not the full answer."
- "Walk me through what this Git command changed."
- "Ask me one question at a time until I understand."

Avoid using Codex only to paste complete answers. Padawan can help most when
you run the code, read the feedback, and ask about the part that is confusing.

## Generated Courses

Generated courses are saved as drafts. They do not appear in the course list
until validation passes and you publish them.

Validation checks include:

- course schema
- badge metadata
- lesson runtime support
- reference solution results where local validation is available

Use the Drafts page or the CLI:

```bash
padawan course draft list
padawan course draft validate <course-id> --json
padawan course draft publish <course-id>
```

## Troubleshooting

- `codex` is not found: install the Codex CLI and make sure it is on `PATH`.
- Login fails: run `codex login` in a normal terminal outside Padawan.
- A generated course is rejected: open the Drafts page or run validation with
  `--json` to see which lesson or badge failed.
- A follow-up thread cannot resume: start a new explanation from the lesson.
