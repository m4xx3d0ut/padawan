from __future__ import annotations

import os
import platform
import shutil
import subprocess
import tempfile
from pathlib import Path

from .models import GradingRule, Lesson, RuntimeName, RuntimeResult
from .settings import Settings

SAFE_ENV_KEYS = ("PATH", "SYSTEMROOT", "WINDIR", "HOME", "USERPROFILE", "TMPDIR", "TEMP", "TMP")


def runtime_available(runtime: RuntimeName) -> tuple[bool, str]:
    if runtime == "none":
        return True, "No runtime required."
    if runtime == "python":
        return shutil.which("python") is not None or shutil.which(
            "python3"
        ) is not None, "Python runtime"
    if runtime == "bash":
        if platform.system().lower() == "windows" and shutil.which("bash") is None:
            return False, "Bash lessons require Git Bash or WSL on Windows."
        return shutil.which("bash") is not None, "Bash runtime"
    if runtime == "git":
        return shutil.which("git") is not None, "Git runtime"
    return False, f"Unknown runtime {runtime}"


def run_lesson(lesson: Lesson, code: str, settings: Settings) -> RuntimeResult:
    available, detail = runtime_available(lesson.runtime)
    if not available:
        return RuntimeResult(status="unavailable", messages=[detail])
    if lesson.runtime == "none":
        return RuntimeResult(
            status="passed", messages=["Read-only lesson acknowledged."], score_delta=1
        )

    with tempfile.TemporaryDirectory(prefix="padawan-run-") as tmp:
        workspace = Path(tmp)
        try:
            completed = _run_runtime(lesson.runtime, code, workspace, settings)
        except subprocess.TimeoutExpired as exc:
            return RuntimeResult(
                status="error",
                stdout=_limit(exc.stdout or "", settings.runtime_output_limit),
                stderr=_limit((exc.stderr or "") + "\nTimed out.", settings.runtime_output_limit),
                messages=["Execution timed out."],
            )
        except OSError as exc:
            return RuntimeResult(
                status="error", stderr=str(exc), messages=["Execution failed to start."]
            )

        stdout = _limit(completed.stdout, settings.runtime_output_limit)
        stderr = _limit(completed.stderr, settings.runtime_output_limit)
        passed, messages, points = grade(
            lesson.grading, completed.returncode, stdout, stderr, workspace
        )
        status = "passed" if passed else "failed"
        return RuntimeResult(
            status=status,
            stdout=stdout,
            stderr=stderr,
            exit_code=completed.returncode,
            messages=messages,
            score_delta=points if passed else 0,
        )


def _run_runtime(
    runtime: RuntimeName,
    code: str,
    workspace: Path,
    settings: Settings,
) -> subprocess.CompletedProcess[str]:
    env = {key: value for key, value in os.environ.items() if key in SAFE_ENV_KEYS}
    if runtime == "python":
        script = workspace / "solution.py"
        script.write_text(code, encoding="utf-8")
        python_bin = shutil.which("python3") or shutil.which("python") or "python"
        cmd = [python_bin, str(script)]
    elif runtime == "bash":
        script = workspace / "solution.sh"
        script.write_text(code, encoding="utf-8")
        cmd = ["bash", str(script)]
    elif runtime == "git":
        script = workspace / "solution.sh"
        script.write_text("set -e\n" + code, encoding="utf-8")
        cmd = ["bash", str(script)]
    else:
        raise OSError(f"unsupported runtime {runtime}")
    return subprocess.run(
        cmd,
        cwd=workspace,
        env=env,
        text=True,
        capture_output=True,
        timeout=settings.runtime_timeout_seconds,
        check=False,
    )


def grade(
    rules: list[GradingRule],
    exit_code: int,
    stdout: str,
    stderr: str,
    workspace: Path,
) -> tuple[bool, list[str], int]:
    if not rules:
        return (
            exit_code == 0,
            ["Program exited successfully." if exit_code == 0 else "Program exited with an error."],
            1,
        )

    messages: list[str] = []
    points = 0
    all_passed = True
    for rule in rules:
        ok = _check_rule(rule, exit_code, stdout, stderr, workspace)
        if ok:
            points += rule.points
            messages.append(f"Passed {rule.kind}.")
        else:
            all_passed = False
            messages.append(f"Missing {rule.kind}: {rule.value or rule.path}.")
    return all_passed, messages, points


def _check_rule(
    rule: GradingRule, exit_code: int, stdout: str, stderr: str, workspace: Path
) -> bool:
    if rule.kind == "exit_code":
        return exit_code == int(rule.value)
    if rule.kind == "stdout_contains":
        return str(rule.value) in stdout
    if rule.kind == "stderr_contains":
        return str(rule.value) in stderr
    if rule.kind == "file_exists":
        return bool(rule.path) and (workspace / rule.path).exists()
    if rule.kind == "file_contains":
        if not rule.path:
            return False
        path = workspace / rule.path
        return path.exists() and str(rule.value) in path.read_text(encoding="utf-8")
    return False


def _limit(value: str | bytes, limit: int) -> str:
    text = value.decode(errors="replace") if isinstance(value, bytes) else value
    if len(text) <= limit:
        return text
    return text[:limit] + "\n[output truncated]"
