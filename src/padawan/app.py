from __future__ import annotations

import json
import tempfile
import zipfile
from pathlib import Path
from typing import Any, get_args

from fastapi import (
    BackgroundTasks,
    FastAPI,
    File,
    HTTPException,
    Request,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from . import __version__
from .backup import BackupError, export_backup, import_backup, inspect_backup
from .codex import CodexClient
from .courses import (
    CourseLoadError,
    export_course,
    find_lesson,
    load_course_dirs,
    load_drafts,
    publish_draft,
    reject_draft,
    validate_course_for_publish,
    validate_course_path,
)
from .docs import list_docs, render_doc
from .models import ConceptLink, Course, Lesson, Level, RuntimeRequest, Track
from .peer import (
    PeerHub,
    PeerIdentityRequest,
    PeerJoinRequest,
    PeerSessionRequest,
    decode_invite_token,
    ice_servers_for_profile,
)
from .runtime import run_lesson
from .settings import PACKAGE_DIR, Settings, ensure_settings_dirs
from .storage import Storage

TEMPLATES = Jinja2Templates(directory=str(PACKAGE_DIR / "templates"))
BACKUP_UPLOAD = File(...)


TRACK_GUIDANCE: dict[str, str] = {
    "linux-bash": (
        "Shell lessons are about command behavior and text flow. Read the command "
        "from left to right, identify what input it receives, then run the smallest "
        "command that proves the output or file changed as expected."
    ),
    "git": (
        "Git lessons are about repository state. Before running a command, name the "
        "state you expect to change: working tree, staging area, commit history, "
        "branch pointer, or remote reference."
    ),
    "python": (
        "Python lessons usually practice one language building block at a time. "
        "Trace the values in the starter code, make one focused edit, then compare "
        "the runtime output with the prompt."
    ),
    "webdev-ts-react": (
        "TypeScript and React lessons ask you to separate data, rendering, and user "
        "interaction. Keep the component behavior small, then use the runtime result "
        "to confirm the rendered state matches the prompt."
    ),
    "webdev-python-htmx": (
        "Python and HTMX lessons connect server-rendered HTML with browser actions. "
        "Look for the request, the response fragment, and the DOM target that should "
        "change after the interaction."
    ),
    "k1s-workerbee": (
        "k1s and WorkerBee lessons are evidence-driven. Describe the desired state, "
        "run or inspect the smallest check available, then compare the observed "
        "status, logs, or probe output with the expected state."
    ),
    "roblox": (
        "Roblox lessons focus on gameplay behavior and Lua scripting concepts. Name "
        "the object, event, or script responsibility first, then explain how it would "
        "change the player experience."
    ),
    "unity": (
        "Unity lessons connect scene objects, components, scripts, and events. Start "
        "by naming which GameObject or Component owns the behavior, then describe the "
        "smallest script or editor change that would prove it."
    ),
    "unreal": (
        "Unreal lessons use engine roles such as Actors, Components, Pawns, "
        "Controllers, and GameMode. Identify which engine object should own the "
        "behavior before choosing Blueprint or C++ details."
    ),
}


TRACK_LINKS: dict[str, list[ConceptLink]] = {
    "linux-bash": [
        ConceptLink(
            title="Bash Reference Manual",
            url="https://www.gnu.org/software/bash/manual/bash.html",
            description="GNU's reference for shell syntax, expansion, variables, and control flow.",
        ),
        ConceptLink(
            title="GNU Coreutils Manual",
            url="https://www.gnu.org/software/coreutils/manual/coreutils.html",
            description="Reference for common commands used in shell lessons.",
        ),
    ],
    "git": [
        ConceptLink(
            title="Pro Git Book",
            url="https://git-scm.com/book/en/v2",
            description=(
                "Beginner-friendly chapters on repositories, commits, branches, and remotes."
            ),
        ),
        ConceptLink(
            title="Git Command Reference",
            url="https://git-scm.com/docs",
            description="Official command documentation for checking exact flags and behavior.",
        ),
    ],
    "python": [
        ConceptLink(
            title="Python Tutorial",
            url="https://docs.python.org/3/tutorial/index.html",
            description="The official guided introduction to Python language basics.",
        ),
        ConceptLink(
            title="Built-in Functions",
            url="https://docs.python.org/3/library/functions.html",
            description="Reference for functions such as print, len, range, and input.",
        ),
    ],
    "webdev-ts-react": [
        ConceptLink(
            title="React Learn",
            url="https://react.dev/learn",
            description="Official React learning path for components, state, and events.",
        ),
        ConceptLink(
            title="TypeScript Handbook",
            url="https://www.typescriptlang.org/docs/handbook/intro.html",
            description="Official TypeScript guide for types, functions, objects, and narrowing.",
        ),
        ConceptLink(
            title="MDN JavaScript Guide",
            url="https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide",
            description="Beginner-friendly JavaScript concepts from MDN.",
        ),
    ],
    "webdev-python-htmx": [
        ConceptLink(
            title="HTMX Documentation",
            url="https://htmx.org/docs/",
            description="Official docs for hx-get, hx-post, swaps, targets, and request flow.",
        ),
        ConceptLink(
            title="FastAPI Tutorial",
            url="https://fastapi.tiangolo.com/tutorial/",
            description="Official step-by-step guide for Python web endpoints.",
        ),
        ConceptLink(
            title="Python Tutorial",
            url="https://docs.python.org/3/tutorial/index.html",
            description="Official Python language basics used by server-side lessons.",
        ),
    ],
    "k1s-workerbee": [
        ConceptLink(
            title="Padawan WorkerBee Guide",
            url="/docs/workerbee",
            description="Local Padawan guidance for WorkerBee validation and progress surfaces.",
        ),
        ConceptLink(
            title="Kubernetes Workloads",
            url="https://kubernetes.io/docs/concepts/workloads/",
            description="Upstream concepts for pods, deployments, and workload state.",
        ),
    ],
    "roblox": [
        ConceptLink(
            title="Roblox Creator Documentation",
            url="https://create.roblox.com/docs",
            description="Official Roblox Creator Hub docs for Studio and engine concepts.",
        ),
        ConceptLink(
            title="Roblox Scripting",
            url="https://create.roblox.com/docs/scripting",
            description="Official scripting overview for adding behavior to Roblox experiences.",
        ),
    ],
    "unity": [
        ConceptLink(
            title="Unity Documentation",
            url="https://docs.unity.com/",
            description="Official entry point for Unity Engine, Editor, and tool documentation.",
        ),
        ConceptLink(
            title="Programming In Unity",
            url="https://docs.unity3d.com/6000.4/Documentation/Manual/scripting.html",
            description="Unity manual section for scripts, components, and programming setup.",
        ),
    ],
    "unreal": [
        ConceptLink(
            title="Unreal Engine Documentation",
            url="https://dev.epicgames.com/documentation/unreal-engine",
            description=(
                "Official Unreal Engine docs for editor, gameplay, Blueprint, and C++ topics."
            ),
        ),
        ConceptLink(
            title="Gameplay Framework",
            url=(
                "https://dev.epicgames.com/documentation/unreal-engine/"
                "gameplay-framework-in-unreal-engine"
            ),
            description="Official guide to Unreal gameplay classes and ownership responsibilities.",
        ),
    ],
}


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved = settings or Settings()
    ensure_settings_dirs(resolved)
    storage = Storage(resolved.db_path)
    codex = CodexClient(resolved)
    app = FastAPI(
        title="Padawan",
        version=__version__,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.state.settings = resolved
    app.state.storage = storage
    app.state.codex = codex
    app.state.peer_hub = PeerHub()
    app.mount("/static", StaticFiles(directory=str(PACKAGE_DIR / "static")), name="static")

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "connect-src 'self' ws: wss:; "
            "form-action 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'",
        )
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers["Strict-Transport-Security"] = "max-age=31536000"
        return response

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request) -> HTMLResponse:
        courses = _courses(resolved)
        context = _base_context(request, resolved, storage)
        context["courses"] = storage.course_cards(courses.values())
        context["tracks"] = get_args(Track)
        context["levels"] = get_args(Level)
        return TEMPLATES.TemplateResponse(request, "index.html", context)

    @app.get("/peer", response_class=HTMLResponse)
    async def peer_workspace(request: Request) -> HTMLResponse:
        courses = _courses(resolved)
        context = _base_context(request, resolved, storage)
        context.update(
            {
                "courses": storage.course_cards(courses.values()),
                "selected_role": request.query_params.get("role", "padawan"),
                "selected_username": request.query_params.get("username", ""),
            }
        )
        return TEMPLATES.TemplateResponse(request, "peer.html", context)

    @app.get("/peer/ice-config")
    async def peer_ice_config(profile: str = "local-turn") -> JSONResponse:
        return JSONResponse(
            {
                "ok": True,
                "profile": profile,
                "ice_servers": ice_servers_for_profile(
                    profile,
                    turn_host=resolved.turn_host,
                    turn_secret=resolved.turn_secret,
                ),
            }
        )

    @app.post("/peer/identity")
    async def peer_identity(request: Request) -> JSONResponse:
        payload = PeerIdentityRequest.model_validate(await request.json())
        identity = storage.peer_identity(payload.username, payload.role)
        return JSONResponse({"ok": True, "identity": identity.model_dump()})

    @app.post("/peer/sessions")
    async def peer_session_create(request: Request) -> JSONResponse:
        payload = PeerSessionRequest.model_validate(await request.json())
        identity = storage.peer_identity(payload.username, payload.role)
        session, token = app.state.peer_hub.create_session(
            issuer=identity,
            ice_profile=payload.ice_profile,
            origin=payload.origin or str(request.base_url).rstrip("/"),
            ttl_seconds=payload.ttl_seconds,
        )
        return JSONResponse(
            {
                "ok": True,
                "identity": identity.model_dump(),
                "session": session.model_dump(),
                "token": token,
            }
        )

    @app.post("/peer/sessions/join")
    async def peer_session_join(request: Request) -> JSONResponse:
        payload = PeerJoinRequest.model_validate(await request.json())
        try:
            token = decode_invite_token(payload.token)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        identity = storage.peer_identity(payload.username, payload.role)
        try:
            session = app.state.peer_hub.join_session(token, identity)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return JSONResponse(
            {"ok": True, "identity": identity.model_dump(), "session": session.model_dump()}
        )

    @app.get("/peer/progress/{course_id}")
    async def peer_local_progress(course_id: str) -> JSONResponse:
        return JSONResponse({"ok": True, "progress": storage.local_progress_payload(course_id)})

    @app.post("/peer/progress")
    async def peer_progress_save(request: Request) -> JSONResponse:
        payload = await request.json()
        peer_id = str(payload.get("peer_id", "")).strip()
        course_id = str(payload.get("course_id", "")).strip()
        progress = payload.get("progress")
        if not peer_id or not course_id or not isinstance(progress, dict):
            return JSONResponse(
                {"ok": False, "error": "peer_id, course_id, and progress are required."},
                status_code=400,
            )
        storage.upsert_peer_progress(peer_id=peer_id, course_id=course_id, payload=progress)
        return JSONResponse({"ok": True})

    @app.post("/peer/courses")
    async def peer_course_save(request: Request) -> JSONResponse:
        payload = await request.json()
        peer_id = str(payload.get("peer_id", "")).strip()
        course = payload.get("course")
        if not peer_id or not isinstance(course, dict):
            return JSONResponse(
                {"ok": False, "error": "peer_id and course are required."},
                status_code=400,
            )
        parsed = Course.model_validate(course)
        export_course(parsed, resolved.user_course_dir / f"{parsed.id}.json")
        inbox_id = storage.record_peer_course(
            peer_id=peer_id,
            course_id=parsed.id,
            course_payload=parsed.model_dump(),
            status="imported",
        )
        return JSONResponse({"ok": True, "inbox_id": inbox_id, "course_id": parsed.id})

    @app.get("/peer/courses/{course_id}/export")
    async def peer_course_export(course_id: str) -> JSONResponse:
        course = _courses(resolved).get(course_id)
        if not course:
            return JSONResponse({"ok": False, "error": "Course not found."}, status_code=404)
        return JSONResponse({"ok": True, "course": course.model_dump()})

    @app.websocket("/peer/ws/{session_id}")
    async def peer_signaling_socket(websocket: WebSocket, session_id: str) -> None:
        raw_token = websocket.query_params.get("token", "")
        peer_id_value = websocket.query_params.get("peer_id", "")
        try:
            app.state.peer_hub.validate(session_id, raw_token)
            await app.state.peer_hub.connect(session_id, peer_id_value, websocket)
            while True:
                payload = await websocket.receive_json()
                if isinstance(payload, dict):
                    await app.state.peer_hub.broadcast(session_id, peer_id_value, payload)
        except ValueError:
            await websocket.close(code=1008)
        except WebSocketDisconnect:
            app.state.peer_hub.disconnect(session_id, peer_id_value)

    @app.get("/courses", response_class=HTMLResponse)
    async def courses_index(request: Request) -> HTMLResponse:
        courses = _courses(resolved)
        context = _base_context(request, resolved, storage)
        cards = storage.course_cards(courses.values())
        track = request.query_params.get("track", "")
        level = request.query_params.get("level", "")
        if track:
            cards = [card for card in cards if card.track == track]
        if level:
            cards = [card for card in cards if card.level == level]
        context.update(
            {
                "courses": cards,
                "tracks": get_args(Track),
                "levels": get_args(Level),
                "selected_track": track,
                "selected_level": level,
            }
        )
        return TEMPLATES.TemplateResponse(request, "courses.html", context)

    @app.get("/courses/{course_id}", response_class=HTMLResponse)
    async def course_detail(request: Request, course_id: str) -> HTMLResponse:
        return await lesson_view(request, course_id, "")

    @app.get("/courses/{course_id}/lessons/{lesson_id}", response_class=HTMLResponse)
    async def lesson_view(request: Request, course_id: str, lesson_id: str) -> HTMLResponse:
        courses = _courses(resolved)
        course = courses.get(course_id)
        if not course:
            return TEMPLATES.TemplateResponse(
                request,
                "error.html",
                {**_base_context(request, resolved, storage), "message": "Course not found."},
                status_code=404,
            )
        if not lesson_id:
            lesson_id = course.lessons[0].id if course.lessons else ""
        try:
            module, lesson = find_lesson(course, lesson_id)
        except KeyError:
            module, lesson = course.modules[0], course.lessons[0]
        context = _base_context(request, resolved, storage)
        context.update(
            {
                "course": course,
                "course_card": storage.course_card(course),
                "module": module,
                "lesson": lesson,
                "lesson_statuses": {
                    item.id: storage.lesson_status(course.id, item.id) for item in course.lessons
                },
                "concept_html": _render_markdown(lesson.concept_md),
                "concept_guide": _lesson_concept_guide(course, lesson),
            }
        )
        return TEMPLATES.TemplateResponse(request, "lesson.html", context)

    @app.post("/runtime/run")
    async def runtime_run(request: Request) -> JSONResponse:
        payload = await request.json()
        runtime_request = RuntimeRequest.model_validate(payload)
        course = _courses(resolved)[runtime_request.course_id]
        _, lesson = find_lesson(course, runtime_request.lesson_id)
        result = run_lesson(lesson, runtime_request.code, resolved)
        storage.record_attempt(course, lesson.id, result)
        return JSONResponse(result.model_dump())

    @app.post("/attempts")
    async def attempts(request: Request) -> JSONResponse:
        payload = await request.json()
        return JSONResponse({"ok": True, "received": payload})

    @app.post("/lessons/{lesson_id}/hint", response_class=HTMLResponse)
    async def hint(request: Request, lesson_id: str) -> HTMLResponse:
        course_id = request.query_params.get("course_id", "")
        course = _courses(resolved).get(course_id)
        hint_text = ""
        if course:
            try:
                _, lesson = find_lesson(course, lesson_id)
                hint_text = lesson.hidden_hint
            except KeyError:
                hint_text = ""
        return TEMPLATES.TemplateResponse(
            request,
            "partials/hint.html",
            {"request": request, "hint": hint_text or "No hint is available for this lesson."},
        )

    @post_or_get(app, "/courses/generate")
    async def generate_course(request: Request) -> JSONResponse:
        payload = await _payload(request)
        prompt = str(payload.get("prompt", "")).strip()
        if not prompt:
            return JSONResponse({"ok": False, "error": "Prompt is required."}, status_code=400)
        job_id = storage.create_generation_job(prompt)
        status = codex.status()
        if not (status.installed and status.authenticated):
            storage.set_generation_job(job_id, status="blocked", detail=status.detail)
            return JSONResponse(
                {"ok": True, "job_id": job_id, "status": "blocked", "detail": status.detail}
            )
        with tempfile.TemporaryDirectory(prefix="padawan-codex-") as tmp:
            try:
                course = codex.generate_course(prompt, Path(tmp) / "course.schema.json")
            except Exception as exc:  # noqa: BLE001
                storage.set_generation_job(job_id, status="failed", detail=str(exc))
                return JSONResponse(
                    {"ok": False, "job_id": job_id, "error": str(exc)}, status_code=500
                )
        storage.set_generation_job(
            job_id,
            status="needs-validation",
            detail="Course draft generated but not published.",
            course_id=course.id,
        )
        export_course(course, resolved.course_draft_dir / f"{course.id}.json")
        return JSONResponse(
            {
                "ok": True,
                "job_id": job_id,
                "status": "needs-validation",
                "course": course.model_dump(),
            }
        )

    @app.get("/drafts", response_class=HTMLResponse)
    async def drafts_index(request: Request) -> HTMLResponse:
        context = _base_context(request, resolved, storage)
        context.update(_draft_context(resolved, storage))
        context["draft_result"] = None
        context["draft_error"] = None
        return TEMPLATES.TemplateResponse(request, "drafts.html", context)

    @app.post("/drafts/{course_id}/validate", response_class=HTMLResponse)
    async def draft_validate(request: Request, course_id: str) -> HTMLResponse:
        context = _base_context(request, resolved, storage)
        try:
            course = load_drafts(resolved.course_draft_dir)[course_id]
            run_id = storage.create_validation_run(
                course_id, "running", "Running local course validation."
            )
            result = validate_course_for_publish(
                course,
                resolved,
                existing_course_ids=set(_courses(resolved)),
            )
            storage.set_validation_run(run_id, result.status, result.model_dump_json())
            context["draft_result"] = result
            context["draft_error"] = None
        except (CourseLoadError, KeyError, OSError, ValueError) as exc:
            context["draft_result"] = None
            context["draft_error"] = str(exc)
        context.update(_draft_context(resolved, storage))
        return TEMPLATES.TemplateResponse(request, "drafts.html", context)

    @app.post("/drafts/{course_id}/validate/start")
    async def draft_validate_start(
        course_id: str,
        background_tasks: BackgroundTasks,
    ) -> JSONResponse:
        try:
            load_drafts(resolved.course_draft_dir)[course_id]
        except (CourseLoadError, KeyError, OSError, ValueError) as exc:
            return JSONResponse({"ok": False, "error": str(exc)}, status_code=404)
        run_id = storage.create_validation_run(
            course_id,
            "queued",
            "Queued for local validation. WorkerBee validation can report through "
            "this status surface when attached.",
        )
        background_tasks.add_task(
            _run_draft_validation_job,
            resolved,
            run_id,
            course_id,
            set(_courses(resolved)),
        )
        return JSONResponse(
            {
                "ok": True,
                "run_id": run_id,
                "validation": _validation_payload(storage.validation_run(run_id)),
            }
        )

    @app.post("/drafts/{course_id}/publish", response_class=HTMLResponse)
    async def draft_publish(request: Request, course_id: str) -> HTMLResponse:
        context = _base_context(request, resolved, storage)
        try:
            result = publish_draft(
                resolved,
                course_id,
                existing_course_ids=set(_courses(resolved)),
            )
            storage.record_validation_run(course_id, result.status, result.model_dump_json())
            context["draft_result"] = result
            context["draft_error"] = None if result.status == "passed" else "Validation failed."
        except (CourseLoadError, KeyError, OSError, ValueError) as exc:
            context["draft_result"] = None
            context["draft_error"] = str(exc)
        context.update(_draft_context(resolved, storage))
        return TEMPLATES.TemplateResponse(request, "drafts.html", context)

    @app.post("/drafts/{course_id}/reject", response_class=HTMLResponse)
    async def draft_reject(request: Request, course_id: str) -> HTMLResponse:
        context = _base_context(request, resolved, storage)
        try:
            reject_draft(resolved, course_id)
            context["draft_result"] = None
            context["draft_error"] = None
        except OSError as exc:
            context["draft_result"] = None
            context["draft_error"] = str(exc)
        context.update(_draft_context(resolved, storage))
        return TEMPLATES.TemplateResponse(request, "drafts.html", context)

    @app.get("/data", response_class=HTMLResponse)
    async def data_index(request: Request) -> HTMLResponse:
        context = _base_context(request, resolved, storage)
        context["backup_summary"] = None
        context["restore_summary"] = None
        context["data_error"] = None
        return TEMPLATES.TemplateResponse(request, "data.html", context)

    @app.get("/data/export")
    async def data_export() -> FileResponse:
        summary = export_backup(resolved)
        return FileResponse(
            summary.archive,
            media_type="application/zip",
            filename=summary.archive.name,
        )

    @app.post("/data/import", response_class=HTMLResponse)
    async def data_import(request: Request, backup: UploadFile = BACKUP_UPLOAD) -> HTMLResponse:
        context = _base_context(request, resolved, storage)
        try:
            with tempfile.NamedTemporaryFile(suffix=".zip") as tmp:
                while chunk := await backup.read(1024 * 1024):
                    tmp.write(chunk)
                tmp.flush()
                context["backup_summary"] = inspect_backup(Path(tmp.name))
                context["restore_summary"] = import_backup(resolved, Path(tmp.name))
                context["data_error"] = None
        except (BackupError, OSError, ValueError, zipfile.BadZipFile) as exc:
            context["backup_summary"] = None
            context["restore_summary"] = None
            context["data_error"] = str(exc)
        return TEMPLATES.TemplateResponse(request, "data.html", context)

    @app.get("/jobs/{job_id}")
    async def job(job_id: int) -> JSONResponse:
        payload = storage.generation_job(job_id)
        if not payload:
            return JSONResponse({"ok": False, "error": "Job not found."}, status_code=404)
        return JSONResponse({"ok": True, "job": payload})

    @app.get("/jobs/{job_id}/events")
    async def job_events(job_id: int) -> JSONResponse:
        payload = storage.generation_job(job_id)
        return JSONResponse(
            {"events": [] if not payload else [{"type": payload["status"], "job": payload}]}
        )

    @app.get("/validations/{run_id}")
    async def validation_status(run_id: int) -> JSONResponse:
        payload = storage.validation_run(run_id)
        if not payload:
            return JSONResponse(
                {"ok": False, "error": "Validation run not found."}, status_code=404
            )
        return JSONResponse({"ok": True, "validation": _validation_payload(payload)})

    @app.post("/codex/explain")
    async def codex_explain(request: Request) -> JSONResponse:
        payload = await request.json()
        courses = _courses(resolved)
        course = courses.get(str(payload.get("course_id", "")))
        if not course:
            return JSONResponse({"ok": False, "error": "Course not found."}, status_code=404)
        _, lesson = find_lesson(course, str(payload.get("lesson_id", "")))
        result = codex.explain(
            course_title=course.title,
            lesson_title=lesson.title,
            prompt=lesson.prompt,
            code=str(payload.get("code", "")),
        )
        if thread_id := result.get("thread_id"):
            storage.upsert_codex_thread(
                thread_id=str(thread_id),
                course_id=course.id,
                lesson_id=lesson.id,
                title=f"{course.title}: {lesson.title}",
            )
        return JSONResponse(result)

    @app.post("/codex/chat/{thread_id}")
    async def codex_chat(thread_id: str, request: Request) -> JSONResponse:
        payload = await request.json()
        message = str(payload.get("message", "")).strip()
        if not message:
            return JSONResponse({"ok": False, "error": "Message is required."}, status_code=400)
        result = codex.chat(thread_id=thread_id, message=message)
        thread = storage.codex_thread(thread_id)
        if thread:
            storage.upsert_codex_thread(
                thread_id=thread_id,
                course_id=str(thread["course_id"]),
                lesson_id=str(thread["lesson_id"]),
                title=str(thread["title"]),
            )
        return JSONResponse(result)

    @app.get("/docs", response_class=HTMLResponse)
    async def docs_index(request: Request) -> HTMLResponse:
        context = _base_context(request, resolved, storage)
        context["docs"] = list_docs(resolved.docs_dir)
        return TEMPLATES.TemplateResponse(request, "docs.html", context)

    @app.get("/docs/{slug}", response_class=HTMLResponse)
    async def docs_page(request: Request, slug: str) -> HTMLResponse:
        context = _base_context(request, resolved, storage)
        try:
            title, body = render_doc(resolved.docs_dir, slug)
        except FileNotFoundError:
            return TEMPLATES.TemplateResponse(
                request,
                "error.html",
                {**context, "message": "Doc not found."},
                status_code=404,
            )
        context.update({"title": title, "body": body, "docs": list_docs(resolved.docs_dir)})
        return TEMPLATES.TemplateResponse(request, "doc_page.html", context)

    @app.get("/healthz")
    async def healthz() -> JSONResponse:
        errors = validate_course_path(resolved.content_dir)
        return JSONResponse(
            {
                "ok": not errors,
                "service": "padawan",
                "db": str(resolved.db_path),
                "course_errors": errors,
            },
            status_code=200 if not errors else 503,
        )

    return app


def _courses(settings: Settings):
    return load_course_dirs(settings.content_dir, settings.user_course_dir)


def _run_draft_validation_job(
    settings: Settings,
    run_id: int,
    course_id: str,
    existing_course_ids: set[str],
) -> None:
    storage = Storage(settings.db_path)
    storage.set_validation_run(run_id, "running", "Running local course validation.")
    try:
        course = load_drafts(settings.course_draft_dir)[course_id]
        result = validate_course_for_publish(
            course,
            settings,
            existing_course_ids=existing_course_ids,
        )
        storage.set_validation_run(run_id, result.status, result.model_dump_json())
    except (CourseLoadError, KeyError, OSError, ValueError) as exc:
        storage.set_validation_run(run_id, "failed", str(exc))


def _draft_context(settings: Settings, storage: Storage) -> dict[str, Any]:
    drafts = []
    for course in load_drafts(settings.course_draft_dir).values():
        drafts.append(
            {
                "course": course,
                "validation": _validation_payload(storage.latest_validation_for_course(course.id)),
            }
        )
    return {"drafts": sorted(drafts, key=lambda item: item["course"].title)}


def _validation_payload(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if not row:
        return None
    detail = str(row.get("detail") or "")
    summary = detail
    messages: list[str] = []
    try:
        parsed = json.loads(detail)
    except ValueError:
        parsed = None
    if isinstance(parsed, dict):
        messages = [str(message) for message in parsed.get("messages", [])]
        status = str(parsed.get("status") or row.get("status") or "")
        runnable = parsed.get("runnable_lessons")
        skipped = parsed.get("skipped_lessons")
        if runnable is not None and skipped is not None:
            summary = f"{runnable} validated lessons, {skipped} skipped lessons."
        elif status:
            summary = f"Validation {status}."
        if messages:
            summary = f"{summary} {len(messages)} issue(s) reported."
    return {
        "id": row.get("id"),
        "course_id": row.get("course_id"),
        "status": row.get("status"),
        "detail": detail,
        "summary": summary,
        "messages": messages,
        "created_at": row.get("created_at"),
    }


def _base_context(request: Request, settings: Settings, storage: Storage) -> dict[str, Any]:
    return {
        "request": request,
        "settings": settings,
        "storage": storage,
        "codex_status": request.app.state.codex.status(),
    }


def _lesson_concept_guide(course: Course, lesson: Lesson) -> dict[str, Any]:
    summary = lesson.concept_summary.strip() or _fallback_concept_summary(course, lesson)
    links = lesson.concept_links or TRACK_LINKS.get(course.track, [])
    return {
        "summary_html": _render_markdown(summary),
        "links": [link.model_dump() for link in links],
    }


def _fallback_concept_summary(course: Course, lesson: Lesson) -> str:
    guidance = TRACK_GUIDANCE.get(
        course.track,
        "Use this lesson to practice one focused concept. Read the prompt, make the "
        "smallest useful change, run it, and compare the result with the expected behavior.",
    )
    return f"Use **{lesson.title}** to practice one focused idea before moving on.\n\n{guidance}"


def _render_markdown(text: str) -> str:
    from markdown_it import MarkdownIt

    return MarkdownIt("commonmark", {"html": False}).render(text)


async def _payload(request: Request) -> dict[str, Any]:
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        body = await request.json()
        return body if isinstance(body, dict) else {}
    form = await request.form()
    return dict(form)


def post_or_get(app: FastAPI, path: str):
    def decorator(func):
        app.post(path)(func)
        app.get(path)(func)
        return func

    return decorator


app = create_app()
