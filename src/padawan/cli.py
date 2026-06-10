from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

from .backup import BackupError, export_backup, import_backup, inspect_backup
from .codex import CodexClient
from .courses import validate_course_path
from .settings import Settings, ensure_settings_dirs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="padawan")
    sub = parser.add_subparsers(dest="command", required=True)

    serve = sub.add_parser("serve", help="Run the local web app")
    serve.add_argument("--host", default=None)
    serve.add_argument("--port", type=int, default=None)

    sub.add_parser("doctor", help="Check local dependencies")

    codex = sub.add_parser("codex", help="Codex helpers")
    codex_sub = codex.add_subparsers(dest="codex_command", required=True)
    codex_sub.add_parser("status", help="Check Codex CLI status")

    course = sub.add_parser("course", help="Course helpers")
    course_sub = course.add_subparsers(dest="course_command", required=True)
    validate = course_sub.add_parser("validate", help="Validate course JSON")
    validate.add_argument("--course", required=True)
    importer = course_sub.add_parser("import-k1s-cip", help="Import k1s Concepts in Practice")
    importer.add_argument("--source", default="../k1s/docs/concepts-in-practice")

    data = sub.add_parser("data", help="Local data backup and restore")
    data_sub = data.add_subparsers(dest="data_command", required=True)
    data_export = data_sub.add_parser("export", help="Export local user data")
    data_export.add_argument("--output", required=True)
    data_inspect = data_sub.add_parser("inspect", help="Inspect a backup archive")
    data_inspect.add_argument("archive")
    data_import = data_sub.add_parser("import", help="Import a backup archive")
    data_import.add_argument("archive")
    data_import.add_argument("--dry-run", action="store_true")

    args = parser.parse_args(argv)
    settings = Settings()
    ensure_settings_dirs(settings)

    if args.command == "serve":
        import uvicorn

        host = args.host or settings.host
        port = args.port or settings.port
        uvicorn.run("padawan.app:app", host=host, port=port, reload=False)
        return 0
    if args.command == "doctor":
        return doctor(settings)
    if args.command == "codex" and args.codex_command == "status":
        status = CodexClient(settings).status()
        print(f"installed: {status.installed}")
        print(f"authenticated: {status.authenticated}")
        print(status.detail)
        return 0 if status.installed else 1
    if args.command == "course" and args.course_command == "validate":
        path = settings.content_dir if args.course == "all-seed" else Path(args.course)
        errors = validate_course_path(path)
        if errors:
            print("\n".join(errors), file=sys.stderr)
            return 1
        print(f"course validation passed: {path}")
        return 0
    if args.command == "course" and args.course_command == "import-k1s-cip":
        return import_k1s_cip(Path(args.source), settings.user_course_dir)
    if args.command == "data":
        return data_command(args, settings)
    parser.error("unknown command")
    return 2


def doctor(settings: Settings) -> int:
    checks = [
        ("python", True, sys.version.split()[0], True),
        ("state_dir", settings.state_dir.exists(), str(settings.state_dir), True),
        ("content_dir", settings.content_dir.exists(), str(settings.content_dir), True),
        ("git", shutil.which("git") is not None, shutil.which("git") or "missing", True),
        ("bash", shutil.which("bash") is not None, shutil.which("bash") or "missing", True),
        (
            "codex",
            shutil.which(settings.codex_bin) is not None,
            shutil.which(settings.codex_bin) or "missing",
            True,
        ),
    ]
    status = CodexClient(settings).status()
    checks.append(("codex_auth", status.authenticated, status.detail, True))
    workerbee = _workerbee_available()
    checks.append(("workerbee", workerbee[0], workerbee[1], False))
    ok = True
    for name, passed, detail, required in checks:
        ok = ok and (passed or not required)
        marker = "ok" if passed else ("optional" if not required else "missing")
        print(f"{marker:8} {name:14} {detail}")
    return 0 if ok else 1


def _workerbee_available() -> tuple[bool, str]:
    path = shutil.which("workerbee")
    if not path:
        return False, "workerbee CLI not on PATH; MCP may still be available in Codex."
    try:
        completed = subprocess.run(
            [path, "--help"], capture_output=True, text=True, timeout=4, check=False
        )
    except OSError as exc:
        return False, str(exc)
    return completed.returncode == 0, path


def data_command(args: argparse.Namespace, settings: Settings) -> int:
    try:
        if args.data_command == "export":
            summary = export_backup(settings, Path(args.output).expanduser())
            print(json.dumps(summary.as_dict(), indent=2, sort_keys=True))
            return 0
        if args.data_command == "inspect":
            summary = inspect_backup(Path(args.archive).expanduser())
            print(json.dumps(summary.as_dict(), indent=2, sort_keys=True))
            return 0
        if args.data_command == "import":
            summary = import_backup(
                settings,
                Path(args.archive).expanduser(),
                dry_run=bool(args.dry_run),
            )
            print(json.dumps(summary.as_dict(), indent=2, sort_keys=True))
            return 0
    except (BackupError, OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 2


def import_k1s_cip(source: Path, out_dir: Path) -> int:
    if not source.exists():
        print(f"source not found: {source}", file=sys.stderr)
        return 1
    out_dir.mkdir(parents=True, exist_ok=True)
    chapters = sorted(path for path in source.glob("*.md") if path.name != "index.md")
    lessons = []
    for index, chapter in enumerate(chapters[:4], start=1):
        text = chapter.read_text(encoding="utf-8")
        title = chapter.stem.replace("-", " ").title()
        for line in text.splitlines():
            if line.startswith("# "):
                title = line[2:].strip()
                break
        lessons.append(
            {
                "id": f"k1s-cip-{index:02d}",
                "title": title,
                "concept_md": text.split("## Commands", 1)[0].strip(),
                "prompt": (
                    "Read the concept and explain one operational check you would run locally."
                ),
                "starter_code": "echo 'check healthz and events'",
                "language": "bash",
                "runtime": "bash",
                "hidden_hint": (
                    "Look for the command block and identify an observe or health command."
                ),
                "grading": [{"kind": "stdout_contains", "value": "health", "points": 1}],
                "codex_context": "k1s Concepts in Practice imported course.",
            }
        )
    course = {
        "id": "k1s-workerbee-concepts",
        "title": "Learn k1s and WorkerBee Concepts",
        "track": "k1s-workerbee",
        "level": "basic",
        "summary": "Interactive starter lessons adapted from k1s Concepts in Practice.",
        "modules": [
            {"id": "cip", "title": "Concepts in Practice", "summary": "", "lessons": lessons}
        ],
        "badges": [
            {
                "id": "k1s-cip-complete",
                "title": "k1s Concepts Starter",
                "description": "Complete the imported k1s Concepts in Practice starter.",
                "criteria": {"completion_percent": 100},
            }
        ],
        "generated": False,
        "verified": True,
    }
    target = out_dir / "k1s-workerbee-concepts.json"
    target.write_text(json.dumps(course, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
