from __future__ import annotations

from pathlib import Path

from markdown_it import MarkdownIt

md = MarkdownIt("commonmark", {"html": False, "linkify": False})


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
    return docs


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
