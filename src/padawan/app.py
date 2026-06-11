from __future__ import annotations

import tempfile
import zipfile
from pathlib import Path
from typing import Any, get_args

from fastapi import FastAPI, File, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

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
from .models import Level, RuntimeRequest, Track
from .runtime import run_lesson
from .settings import PACKAGE_DIR, Settings, ensure_settings_dirs
from .storage import Storage

TEMPLATES = Jinja2Templates(directory=str(PACKAGE_DIR / "templates"))
BACKUP_UPLOAD = File(...)


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved = settings or Settings()
    ensure_settings_dirs(resolved)
    storage = Storage(resolved.db_path)
    codex = CodexClient(resolved)
    app = FastAPI(
        title="Padawan",
        version="0.1.0",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.state.settings = resolved
    app.state.storage = storage
    app.state.codex = codex
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
            result = validate_course_for_publish(
                course,
                resolved,
                existing_course_ids=set(_courses(resolved)),
            )
            storage.record_validation_run(course_id, result.status, result.model_dump_json())
            context["draft_result"] = result
            context["draft_error"] = None
        except (CourseLoadError, KeyError, OSError, ValueError) as exc:
            context["draft_result"] = None
            context["draft_error"] = str(exc)
        context.update(_draft_context(resolved, storage))
        return TEMPLATES.TemplateResponse(request, "drafts.html", context)

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


def _draft_context(settings: Settings, storage: Storage) -> dict[str, Any]:
    drafts = []
    for course in load_drafts(settings.course_draft_dir).values():
        drafts.append(
            {
                "course": course,
                "validation": storage.latest_validation_for_course(course.id),
            }
        )
    return {"drafts": sorted(drafts, key=lambda item: item["course"].title)}


def _base_context(request: Request, settings: Settings, storage: Storage) -> dict[str, Any]:
    return {
        "request": request,
        "settings": settings,
        "storage": storage,
        "codex_status": request.app.state.codex.status(),
    }


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
