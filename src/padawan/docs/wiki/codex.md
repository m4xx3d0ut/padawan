# Codex Integration

Padawan uses the installed Codex CLI as the local ChatGPT/Codex bridge.

```bash
codex login
padawan codex status
```

Padawan does not read or store `~/.codex/auth.json`. It calls `codex exec
--json` for generated explanations and course drafts.

When Codex returns a thread id, Padawan stores lightweight local metadata for the
course and lesson. Follow-up messages use `codex exec resume <thread-id> --json`
so the lesson dialog can continue the same tutoring thread.

Padawan never stores Codex auth files, API keys, or access tokens.
