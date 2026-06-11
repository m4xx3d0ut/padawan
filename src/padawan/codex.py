from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from .models import CodexStatus, Course
from .settings import Settings

COURSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "title": {"type": "string"},
        "track": {"type": "string"},
        "level": {"type": "string"},
        "summary": {"type": "string"},
        "modules": {"type": "array"},
        "badges": {"type": "array"},
        "generated": {"type": "boolean"},
        "verified": {"type": "boolean"},
    },
    "required": ["id", "title", "track", "level", "summary", "modules"],
    "additionalProperties": True,
}


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
        instruction = (
            "Create one Padawan course JSON object for a beginner local coding app. "
            "Use only these tracks: linux-bash, git, python, webdev-ts-react, "
            "webdev-python-htmx, k1s-workerbee, roblox, unity, unreal. "
            "Use level basic, intermediate, or advanced. Include at least one module "
            "and two lessons. "
            "Each lesson must have concept_md, concept_summary, concept_links, "
            "prompt, starter_code, language, runtime, hidden_hint, grading, "
            "codex_context, reference_solution, and toolchain fields. "
            "concept_summary must be two to four novice-friendly sentences that "
            "teach the lesson concept before the exercise. concept_links must be "
            "one to four objects with title, url, and description fields, and must "
            "prefer official project documentation such as Python, Git, GNU Bash, "
            "React, TypeScript, HTMX, FastAPI, Roblox, Unity, Unreal, or Kubernetes "
            "docs as appropriate. Use only python, bash, git, node, text, or none "
            "for runtime. Set generated true and verified false.\n\n"
            f"User request: {prompt}"
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
