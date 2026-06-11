from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tarfile
import tomllib
import zipfile
from pathlib import Path

import pytest

from padawan import __version__
from padawan.app import create_app
from padawan.settings import REPO_ROOT, Settings


def test_shell_installer_is_valid_and_uses_release_wheelhouse() -> None:
    script = REPO_ROOT / "scripts" / "install-padawan.sh"
    proc = subprocess.run(["sh", "-n", str(script)], text=True, capture_output=True, check=False)
    text = script.read_text(encoding="utf-8")

    assert proc.returncode == 0, proc.stderr
    assert "https://github.com/m4xx3d0ut/padawan/releases/latest/download" in text
    assert "padawan-wheelhouse.tar.gz" in text
    assert "pip install --no-compile --no-index --find-links" in text
    assert "pip install --no-compile --find-links" in text
    assert "$padawan_cmd doctor" in text
    assert "$padawan_cmd serve" in text


def test_powershell_installer_is_valid_when_pwsh_is_available() -> None:
    pwsh = shutil.which("pwsh")
    if not pwsh:
        pytest.skip("pwsh is not installed")

    script = REPO_ROOT / "scripts" / "install-padawan.ps1"
    command = f"[scriptblock]::Create((Get-Content -Raw {script!s})) | Out-Null"
    proc = subprocess.run(
        [pwsh, "-NoProfile", "-Command", command],
        text=True,
        capture_output=True,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr


def test_powershell_installer_uses_release_wheelhouse() -> None:
    text = (REPO_ROOT / "scripts" / "install-padawan.ps1").read_text(encoding="utf-8")

    assert "https://github.com/m4xx3d0ut/padawan/releases/latest/download" in text
    assert "padawan-wheelhouse.zip" in text
    assert "--no-index" in text
    assert "--find-links" in text
    assert "$PadawanCmd doctor" in text
    assert "$PadawanCmd serve" in text


def test_build_wheelhouse_script_packages_existing_wheels(tmp_path: Path) -> None:
    wheelhouse = tmp_path / "padawan-wheelhouse"
    release = tmp_path / "release"
    wheelhouse.mkdir()
    (wheelhouse / "padawan-0.1.0-py3-none-any.whl").write_bytes(b"placeholder")

    proc = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "build_wheelhouse.py"),
            "--out",
            str(wheelhouse),
            "--archive-dir",
            str(release),
            "--skip-build",
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    assert (wheelhouse / "INSTALL.txt").exists()
    manifest = json.loads((wheelhouse / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["project"] == "padawan"
    assert manifest["version"] == __version__
    assert manifest["wheel_count"] == 1
    tar_path = release / "padawan-wheelhouse.tar.gz"
    zip_path = release / "padawan-wheelhouse.zip"
    assert tar_path.exists()
    assert zip_path.exists()
    with tarfile.open(tar_path) as archive:
        assert "padawan-wheelhouse/INSTALL.txt" in archive.getnames()
    with zipfile.ZipFile(zip_path) as archive:
        assert "padawan-wheelhouse/manifest.json" in archive.namelist()


def test_release_version_sources_match(tmp_path: Path) -> None:
    project = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    app = create_app(
        Settings(
            state_dir=tmp_path,
            content_dir=REPO_ROOT / "content" / "courses",
            docs_dir=REPO_ROOT / "docs" / "wiki",
        )
    )

    assert project["version"] == __version__
    assert app.version == __version__


def test_changelog_and_release_workflow_cover_current_release() -> None:
    changelog = (REPO_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    workflow = (REPO_ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")

    assert "## Unreleased" in changelog
    assert f"## {__version__} - 2026-06-11" in changelog
    assert "padawan-wheelhouse.tar.gz" in workflow
    assert "padawan-wheelhouse.zip" in workflow
    assert "install-padawan.sh" in workflow
    assert "install-padawan.ps1" in workflow
