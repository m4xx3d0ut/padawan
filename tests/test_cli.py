from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from padawan.settings import REPO_ROOT


def test_data_cli_export_inspect_and_dry_run_import(tmp_path: Path) -> None:
    archive = tmp_path / "backup.zip"
    env = {
        **os.environ,
        "PADAWAN_STATE_DIR": str(tmp_path / "state"),
        "PADAWAN_CONTENT_DIR": str(REPO_ROOT / "content" / "courses"),
        "PADAWAN_DOCS_DIR": str(REPO_ROOT / "docs" / "wiki"),
    }

    exported = subprocess.run(
        [sys.executable, "-m", "padawan.cli", "data", "export", "--output", str(archive)],
        capture_output=True,
        env=env,
        text=True,
        timeout=20,
        check=False,
    )
    inspected = subprocess.run(
        [sys.executable, "-m", "padawan.cli", "data", "inspect", str(archive)],
        capture_output=True,
        env=env,
        text=True,
        timeout=20,
        check=False,
    )
    imported = subprocess.run(
        [sys.executable, "-m", "padawan.cli", "data", "import", str(archive), "--dry-run"],
        capture_output=True,
        env=env,
        text=True,
        timeout=20,
        check=False,
    )

    assert exported.returncode == 0
    assert inspected.returncode == 0
    assert imported.returncode == 0
    assert archive.exists()
    assert json.loads(exported.stdout)["archive"] == str(archive)
    assert json.loads(inspected.stdout)["table_counts"]["attempts"] == 0
    assert json.loads(imported.stdout)["dry_run"] is True
