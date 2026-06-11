from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from .models import CodexStatus, Course, training_data_json_schema
from .settings import PACKAGE_DIR, Settings

COURSE_SCHEMA: dict[str, Any] = training_data_json_schema()
COURSE_GENERATION_PROFILE = PACKAGE_DIR / "prompt_profiles" / "course_generation_v1.md"


class CodexClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def status(self) -> CodexStatus:
        installed = shutil.which(self.settings.codex_bin) is not None
        if not installed:
            return CodexStatus(
                installed=False, authenticated=False, detail="Codex CLI is not on PATH."
            )
        try:
            completed = subprocess.run(
                [self.settings.codex_bin, "login", "status"],
                text=True,
                capture_output=True,
                timeout=8,
                check=False,
            )
        except OSError as exc:
            return CodexStatus(installed=True, authenticated=False, detail=str(exc))
        detail = (completed.stdout + completed.stderr).strip()
        return CodexStatus(
            installed=True,
            authenticated=completed.returncode == 0,
            detail=detail or "Codex login status checked.",
        )

    def explain(
        self, *, course_title: str, lesson_title: str, prompt: str, code: str
    ) -> dict[str, Any]:
        instruction = (
            "You are Padawan, a local coding tutor. Explain the student's issue without "
            "giving away the full solution unless it is necessary. Keep the answer concise.\n\n"
            f"Course: {course_title}\n"
            f"Lesson: {lesson_title}\n"
            f"Prompt: {prompt}\n\n"
            f"Student code:\n{code}"
        )
        return self._exec(instruction)

    def chat(self, *, thread_id: str, message: str) -> dict[str, Any]:
        status = self.status()
        if not status.installed:
            return {"ok": False, "error": status.detail, "final_message": ""}
        if not status.authenticated:
            return {"ok": False, "error": status.detail, "final_message": ""}
        cmd = [self.settings.codex_bin, "exec", "resume", "--json", thread_id, "-"]
        return self._run_json_command(cmd, stdin=message)

    def generate_course(self, prompt: str, schema_path: Path) -> Course:
        schema_path.write_text(json.dumps(COURSE_SCHEMA, indent=2), encoding="utf-8")
        instruction = COURSE_GENERATION_PROFILE.read_text(encoding="utf-8").replace(
            "{{USER_REQUEST}}", prompt
        )
        result = self._exec(instruction, schema_path=schema_path)
        text = result.get("final_message", "")
        return Course.model_validate_json(text)

    def _exec(self, instruction: str, *, schema_path: Path | None = None) -> dict[str, Any]:
        status = self.status()
        if not status.installed:
            return {"ok": False, "error": status.detail, "final_message": ""}
        cmd = [self.settings.codex_bin, "exec", "--json", "--sandbox", "read-only"]
        if schema_path:
            cmd.extend(["--output-schema", str(schema_path)])
        cmd.append(instruction)
        return self._run_json_command(cmd)

    def _run_json_command(self, cmd: list[str], *, stdin: str | None = None) -> dict[str, Any]:
        try:
            completed = subprocess.run(
                cmd,
                input=stdin,
                text=True,
                capture_output=True,
                timeout=120,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return {"ok": False, "error": "Codex timed out.", "final_message": ""}
        events = _parse_jsonl(completed.stdout)
        final_message = ""
        thread_id = None
        for event in events:
            if event.get("type") == "thread.started":
                thread_id = event.get("thread_id")
            item = event.get("item")
            if isinstance(item, dict) and item.get("type") == "agent_message":
                final_message = str(item.get("text", ""))
        if not final_message and completed.stdout.strip() and not events:
            final_message = completed.stdout.strip()
        return {
            "ok": completed.returncode == 0,
            "returncode": completed.returncode,
            "thread_id": thread_id,
            "events": events,
            "final_message": final_message,
            "stderr": completed.stderr,
        }


def _parse_jsonl(text: str) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for line in text.splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            events.append(payload)
    return events
