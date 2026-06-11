from __future__ import annotations

from pathlib import Path

from markdown_it import MarkdownIt

md = MarkdownIt("commonmark", {"html": False, "linkify": False})
DOC_ORDER = {
    "first-steps": 0,
    "install": 1,
    "runtime-safety": 2,
    "data-backup": 3,
    "codex": 4,
    "course-authoring": 5,
    "badges": 6,
    "workerbee": 7,
    "qa-uat": 8,
    "troubleshooting": 9,
}


def list_docs(docs_dir: Path) -> list[dict[str, str]]:
    if not docs_dir.exists():
        return []
    docs = []
    for path in sorted(docs_dir.glob("*.md")):
        title = path.stem.replace("-", " ").title()
        first = path.read_text(encoding="utf-8").splitlines()[:5]
        for line in first:
            if line.startswith("# "):
                title = line[2:].strip()
                break
        docs.append({"slug": path.stem, "title": title})
    return sorted(docs, key=lambda doc: (DOC_ORDER.get(doc["slug"], 100), doc["title"]))


def render_doc(docs_dir: Path, slug: str) -> tuple[str, str]:
    path = docs_dir / f"{slug}.md"
    if not path.exists():
        raise FileNotFoundError(slug)
    text = path.read_text(encoding="utf-8")
    title = slug.replace("-", " ").title()
    for line in text.splitlines()[:8]:
        if line.startswith("# "):
            title = line[2:].strip()
            break
    return title, md.render(text)
