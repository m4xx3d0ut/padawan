# Install Padawan

Padawan runs locally with Python 3.11 or newer. You do not need a cloud account
to use bundled courses. Codex features require the Codex CLI, and WorkerBee
validation requires WorkerBee.

Run commands from the repository root.

## Choose Your Path

Use the beginner path if you only want to run Padawan and try lessons. Use the
developer path if you are changing code, course files, or WorkerBee manifests.

## One-Line Release Install

Use this path if you want Padawan installed without cloning the repository.

Linux and macOS:

```bash
curl -fsSL https://github.com/m4xx3d0ut/padawan/releases/latest/download/install-padawan.sh | sh
padawan doctor
padawan serve
```

Windows PowerShell:

```powershell
irm https://github.com/m4xx3d0ut/padawan/releases/latest/download/install-padawan.ps1 | iex
padawan doctor
padawan serve
```

Open:

```text
http://127.0.0.1:8787/
```

The installer uses your active Python virtual environment when one is active.
Otherwise, it creates a standalone Padawan virtual environment in your local app
data directory and writes a `padawan` wrapper.

If the installer prints a PATH command, run it before `padawan doctor`.

### Install From Downloaded Release Artifacts

If you downloaded the release files manually, put the installer and wheelhouse in
the same directory.

Linux and macOS:

```bash
chmod +x install-padawan.sh
PADAWAN_INSTALL_BASE_URL="file://$(pwd)" ./install-padawan.sh
```

Windows PowerShell:

```powershell
$env:PADAWAN_INSTALL_BASE_URL = "file:///$((Get-Location).Path.Replace('\', '/'))"
.\install-padawan.ps1
```

Expected release artifacts:

```text
install-padawan.sh
install-padawan.ps1
padawan-wheelhouse.tar.gz
padawan-wheelhouse.zip
```

## Super Newcomer Setup

Use this section if you are new to command-line projects or setting up a coding
workspace for the first time.

### 1. Install The Required Tools

Install these first:

- Python 3.11 or newer: [Python downloads](https://www.python.org/downloads/)
- Git: [Installing Git](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git)

Optional but useful:

- Node.js, for WebDev TS/React lessons:
  [Node.js downloads](https://nodejs.org/en/download)
- WSL, if you are on Windows and want a Linux-like Bash shell:
  [Install WSL](https://learn.microsoft.com/en-us/windows/wsl/install)

After installing Python and Git, open a new terminal so your system can find the
new commands.

Check the tools:

```bash
python --version
git --version
```

If `python` is not found on Linux or macOS, try `python3 --version` and use
`python3` anywhere this guide says `python`.

On Windows, Python may be available as `py` instead:

```powershell
py --version
git --version
```

### 2. Make A Projects Directory

Pick one folder where coding projects will live. Avoid system folders such as
`C:\Windows`, `/usr`, or `/Applications`.

Linux and macOS:

```bash
mkdir -p ~/code
cd ~/code
```

Windows PowerShell:

```powershell
mkdir $HOME\code
cd $HOME\code
```

### 3. Get The Padawan Repo

Clone the repo into your projects directory:

```bash
git clone https://github.com/m4xx3d0ut/padawan.git
cd padawan
```

If you already downloaded a zip file instead, unzip it into your projects
directory and `cd` into the unzipped `padawan` folder.

### 4. Create A Python Virtual Environment

A virtual environment keeps Padawan's Python packages separate from the rest of
your computer. Python's standard `venv` module is documented here:
[venv](https://docs.python.org/3/library/venv.html).

Linux and macOS:

```bash
python -m venv .venv
. .venv/bin/activate
```

Windows PowerShell:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

When the environment is active, your prompt usually starts with `(.venv)`.

### 5. Install And Run Padawan

```bash
python -m pip install --upgrade pip setuptools wheel
python -m pip install -e .[dev]
padawan doctor
padawan serve
```

Open:

```text
http://127.0.0.1:8787/
```

Keep the terminal open while using Padawan. Stop it with `Ctrl+C`.

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

Build a local release wheelhouse:

```bash
scripts/build_wheelhouse.sh --python .venv/bin/python
```

Install from that local wheelhouse:

```bash
python -m pip install --no-index --find-links dist/padawan-wheelhouse padawan
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
