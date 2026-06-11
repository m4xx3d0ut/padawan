# Install Padawan

Padawan runs locally with Python 3.11 or newer. You do not need a cloud account
to use bundled courses. Codex features require the Codex CLI, and WorkerBee
validation requires WorkerBee.

Run commands from the repository root.

## Choose Your Path

Use the beginner path if you only want to run Padawan and try lessons. Use the
developer path if you are changing code, course files, or WorkerBee manifests.

## Beginner Path

Linux and macOS:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e .[dev]
padawan doctor
padawan serve
```

Windows PowerShell:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .[dev]
padawan doctor
padawan serve
```

Open `http://127.0.0.1:8787/`.

Leave the terminal window open while using the app. Stop the server with
`Ctrl+C`.

## Developer Path

The editable install includes development tools:

```bash
python -m pip install -e .[dev]
ruff format --check
ruff check
pytest
padawan course validate --course all-seed
```

## Optional Local Runtimes

- Bash lessons need Bash. On Windows, use Git Bash or WSL.
- WebDev TS/React lessons use Node.js for local validation.
- Codex features need the Codex CLI and `codex login`.

Python lessons use the same Python environment that runs Padawan.

## Check The Install

Run:

```bash
padawan doctor
```

The doctor command reports the state directory, content directory, docs
directory, database path, Codex CLI availability, and local runtime status.

## Where Data Is Stored

By default, Padawan stores local data in the platform app-data location:

- Linux: `$XDG_DATA_HOME/padawan` or `~/.local/share/padawan`
- macOS: `~/Library/Application Support/Padawan`
- Windows: `%LOCALAPPDATA%\Padawan`

Set `PADAWAN_STATE_DIR` if you want to store data somewhere else:

```bash
PADAWAN_STATE_DIR=/path/to/padawan-data padawan serve
```

## Common Setup Problems

- `python` is not found: install Python 3.11 or newer and reopen the terminal.
- `pip install` fails: upgrade packaging tools with
  `python -m pip install --upgrade pip setuptools wheel`.
- PowerShell blocks activation: run
  `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, then activate again.
- A runtime is unavailable: install the runtime listed by `padawan doctor`.
