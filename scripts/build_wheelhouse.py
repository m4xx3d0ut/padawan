from __future__ import annotations

import argparse
import json
import platform
import shutil
import subprocess
import sys
import tarfile
import tomllib
import zipfile
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_OUT_DIR = ROOT_DIR / "dist" / "padawan-wheelhouse"
ARCHIVE_BASENAME = "padawan-wheelhouse"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build Padawan wheelhouse release artifacts.")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--archive-dir", type=Path, default=None)
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument(
        "--skip-build",
        action="store_true",
        help="Package an existing wheelhouse directory without running pip wheel.",
    )
    args = parser.parse_args(argv)

    out_dir = args.out.resolve()
    archive_dir = (args.archive_dir or out_dir.parent).resolve()
    archive_dir.mkdir(parents=True, exist_ok=True)

    if not args.skip_build:
        shutil.rmtree(out_dir, ignore_errors=True)
        out_dir.mkdir(parents=True, exist_ok=True)
        build_wheels(args.python, out_dir)
    elif not out_dir.exists():
        raise SystemExit(f"wheelhouse does not exist: {out_dir}")

    write_install_txt(out_dir)
    write_manifest(out_dir)
    tar_path = archive_dir / f"{ARCHIVE_BASENAME}.tar.gz"
    zip_path = archive_dir / f"{ARCHIVE_BASENAME}.zip"
    tar_path.unlink(missing_ok=True)
    zip_path.unlink(missing_ok=True)
    write_tarball(out_dir, tar_path)
    write_zip(out_dir, zip_path)

    print(f"wheelhouse: {out_dir}")
    print(f"archive: {tar_path}")
    print(f"archive: {zip_path}")
    return 0


def build_wheels(python: str, out_dir: Path) -> None:
    subprocess.run(
        [
            python,
            "-m",
            "pip",
            "wheel",
            "--wheel-dir",
            str(out_dir),
            str(ROOT_DIR),
        ],
        check=True,
    )


def project_version() -> str:
    project = tomllib.loads((ROOT_DIR / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    return str(project["version"])


def write_install_txt(out_dir: Path) -> None:
    (out_dir / "INSTALL.txt").write_text(
        """Install Padawan from this wheelhouse:

  python -m pip install --no-index --find-links . padawan

Then run:

  padawan doctor
  padawan serve

Optional runtime requirements not bundled in wheels:
  - Git for Git lessons
  - Bash for Bash lessons
  - Node.js for WebDev TS/React lessons
  - Codex CLI for generated explanations and course drafts
  - WorkerBee for publish validation workflows
""",
        encoding="utf-8",
    )


def write_manifest(out_dir: Path) -> None:
    wheels = sorted(path.name for path in out_dir.glob("*.whl"))
    manifest = {
        "project": "padawan",
        "version": project_version(),
        "wheelhouse": ARCHIVE_BASENAME,
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "wheel_count": len(wheels),
        "wheels": wheels,
    }
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_tarball(out_dir: Path, tar_path: Path) -> None:
    with tarfile.open(tar_path, "w:gz") as archive:
        archive.add(out_dir, arcname=ARCHIVE_BASENAME)


def write_zip(out_dir: Path, zip_path: Path) -> None:
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(out_dir.rglob("*")):
            archive.write(path, Path(ARCHIVE_BASENAME) / path.relative_to(out_dir))


if __name__ == "__main__":
    raise SystemExit(main())
