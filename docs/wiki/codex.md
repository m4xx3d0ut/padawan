# Codex Integration

Padawan uses the installed Codex CLI as the local ChatGPT/Codex bridge.

```bash
codex login
padawan codex status
```

Padawan does not read or store `~/.codex/auth.json`. It calls `codex exec
--json` for generated explanations and course drafts.
