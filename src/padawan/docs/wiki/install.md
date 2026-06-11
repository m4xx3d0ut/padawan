# Install Padawan

Padawan runs locally with Python 3.11 or newer.

Linux and macOS:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e .[dev]
padawan doctor
padawan serve
```

On Windows, use PowerShell activation:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .[dev]
padawan doctor
padawan serve
```

Open `http://127.0.0.1:8787/`.

Optional local runtimes:

- Bash lessons need Bash. On Windows, use Git Bash or WSL.
- WebDev TS/React lessons use Node.js for local validation.
- Codex features need the Codex CLI and `codex login`.
