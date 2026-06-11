from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from padawan.app import create_app
from padawan.courses import export_course, load_courses
from padawan.settings import REPO_ROOT, Settings


def make_client(tmp_path: Path) -> TestClient:
    app = create_app(
        Settings(
            state_dir=tmp_path,
            content_dir=REPO_ROOT / "content" / "courses",
            docs_dir=REPO_ROOT / "docs" / "wiki",
        )
    )
    return TestClient(app)


def test_landing_page_renders_courses_and_style(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert "What programming language or skills would you like to learn today?" in response.text
    assert "Python Basics" in response.text
    assert "/static/brand/page-background-3840x2160.webp" not in response.text
    assert "/static/css/app.css" in response.text


def test_lesson_page_runs_python(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        page = client.get("/courses/python-basics/lessons/hello-python")
        response = client.post(
            "/runtime/run",
            json={
                "course_id": "python-basics",
                "lesson_id": "hello-python",
                "runtime": "python",
                "code": "print('Hello, Padawan!')",
            },
        )

    assert page.status_code == 200
    assert "Runtime Shell" in page.text
    assert response.status_code == 200
    assert response.json()["status"] == "passed"


def test_docs_render(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        index = client.get("/docs")
        page = client.get("/docs/install")

    assert index.status_code == 200
    assert "Install Padawan" in index.text
    assert page.status_code == 200
    assert "Python 3.11" in page.text


def test_data_export_and_import_render_summary(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        index = client.get("/data")
        archive = client.get("/data/export")
        imported = client.post(
            "/data/import",
            files={"backup": ("backup.zip", archive.content, "application/zip")},
        )

    assert index.status_code == 200
    assert "Local Data" in index.text
    assert archive.status_code == 200
    assert archive.content.startswith(b"PK")
    assert imported.status_code == 200
    assert "Import Summary" in imported.text


def test_course_filters_and_draft_publish(tmp_path: Path) -> None:
    settings = Settings(
        state_dir=tmp_path,
        content_dir=REPO_ROOT / "content" / "courses",
        docs_dir=REPO_ROOT / "docs" / "wiki",
    )
    draft = load_courses(settings.content_dir)["python-basics"].model_copy(
        update={
            "id": "generated-python",
            "title": "Generated Python",
            "generated": True,
            "verified": False,
        }
    )
    export_course(draft, settings.course_draft_dir / "generated-python.json")

    app = create_app(settings)
    with TestClient(app) as client:
        filtered = client.get("/courses?track=python&level=advanced")
        drafts = client.get("/drafts")
        validated = client.post("/drafts/generated-python/validate")
        published = client.post("/drafts/generated-python/publish")
        courses = client.get("/courses")

    assert filtered.status_code == 200
    assert "Python Advanced" in filtered.text
    assert "Python Basics" not in filtered.text
    assert drafts.status_code == 200
    assert "Generated Python" in drafts.text
    assert validated.status_code == 200
    assert "Validation Result" in validated.text
    assert published.status_code == 200
    assert (settings.user_course_dir / "generated-python.json").exists()
    assert not (settings.course_draft_dir / "generated-python.json").exists()
    assert "Generated Python" in courses.text
