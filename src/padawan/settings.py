from __future__ import annotations

import os
import platform
from dataclasses import dataclass
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
REPO_ROOT = PACKAGE_DIR.parents[1]


def default_state_dir() -> Path:
    override = os.getenv("PADAWAN_STATE_DIR")
    if override:
        return Path(override).expanduser()

    system = platform.system().lower()
    if system == "windows":
        base = Path(os.getenv("LOCALAPPDATA", str(Path.home() / "AppData" / "Local")))
        return base / "Padawan"
    if system == "darwin":
        return Path.home() / "Library" / "Application Support" / "Padawan"
    return Path(os.getenv("XDG_DATA_HOME", str(Path.home() / ".local" / "share"))) / "padawan"


def default_content_dir() -> Path:
    override = os.getenv("PADAWAN_CONTENT_DIR")
    if override:
        return Path(override).expanduser()

    cwd_content = Path.cwd() / "content" / "courses"
    if cwd_content.exists():
        return cwd_content
    repo_content = REPO_ROOT / "content" / "courses"
    if repo_content.exists():
        return repo_content
    return PACKAGE_DIR / "content" / "courses"


def default_docs_dir() -> Path:
    override = os.getenv("PADAWAN_DOCS_DIR")
    if override:
        return Path(override).expanduser()

    cwd_docs = Path.cwd() / "docs" / "wiki"
    if cwd_docs.exists():
        return cwd_docs
    repo_docs = REPO_ROOT / "docs" / "wiki"
    if repo_docs.exists():
        return repo_docs
    return PACKAGE_DIR / "docs" / "wiki"


@dataclass(frozen=True)
class Settings:
    host: str = os.getenv("PADAWAN_HOST", "127.0.0.1")
    port: int = int(os.getenv("PADAWAN_PORT", "8787"))
    state_dir: Path = default_state_dir()
    content_dir: Path = default_content_dir()
    docs_dir: Path = default_docs_dir()
    codex_bin: str = os.getenv("PADAWAN_CODEX_BIN", "codex")
    runtime_timeout_seconds: float = float(os.getenv("PADAWAN_RUNTIME_TIMEOUT", "8"))
    runtime_output_limit: int = int(os.getenv("PADAWAN_RUNTIME_OUTPUT_LIMIT", "12000"))

    @property
    def db_path(self) -> Path:
        return self.state_dir / "padawan.sqlite3"

    @property
    def user_course_dir(self) -> Path:
        return self.state_dir / "courses"

    @property
    def course_draft_dir(self) -> Path:
        return self.state_dir / "course-drafts"

    @property
    def backup_dir(self) -> Path:
        return self.state_dir / "backups"


def ensure_settings_dirs(settings: Settings) -> None:
    settings.state_dir.mkdir(parents=True, exist_ok=True)
    settings.user_course_dir.mkdir(parents=True, exist_ok=True)
    settings.course_draft_dir.mkdir(parents=True, exist_ok=True)
    settings.backup_dir.mkdir(parents=True, exist_ok=True)
