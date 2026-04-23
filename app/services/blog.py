from __future__ import annotations

import os
import re
from typing import Optional

POSTS_DIR = "content/posts"


def _parse_frontmatter(raw: str) -> tuple:
    if not raw.startswith("---"):
        return {}, raw
    parts = raw.split("---", 2)
    if len(parts) < 3:
        return {}, raw
    fm: dict = {}
    for line in parts[1].strip().splitlines():
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        fm[key.strip()] = val.strip()
    return fm, parts[2].strip()


def _render_markdown(text: str) -> str:
    try:
        import markdown as md
        return md.markdown(text, extensions=["fenced_code", "tables"])
    except ImportError:
        # Fallback: wrap paragraphs in <p> tags
        paras = re.split(r"\n{2,}", text.strip())
        return "\n".join(f"<p>{p.replace(chr(10), ' ')}</p>" for p in paras)


def _parse_tags(raw: str) -> list[str]:
    raw = raw.strip()
    if raw.startswith("["):
        raw = raw.strip("[]")
    return [t.strip() for t in raw.split(",") if t.strip()]


def _load_post(path: str, render_body: bool = False) -> Optional[dict]:
    try:
        with open(path, encoding="utf-8") as f:
            raw = f.read()
    except OSError:
        return None

    fm, body = _parse_frontmatter(raw)
    if fm.get("draft", "false").lower() == "true":
        return None

    slug = os.path.basename(path)[:-3]  # strip .md
    tags = _parse_tags(fm.get("tags", ""))
    excerpt = body[:250].rstrip() + ("…" if len(body) > 250 else "")

    return {
        "slug": slug,
        "title": fm.get("title", slug),
        "date": fm.get("date", ""),
        "tags": tags,
        "excerpt": excerpt,
        "body": _render_markdown(body) if render_body else None,
    }


def get_all_posts() -> list[dict]:
    if not os.path.isdir(POSTS_DIR):
        return []
    posts = []
    for fname in os.listdir(POSTS_DIR):
        if not fname.endswith(".md"):
            continue
        post = _load_post(os.path.join(POSTS_DIR, fname))
        if post:
            posts.append(post)
    posts.sort(key=lambda p: p["date"], reverse=True)
    return posts


def get_recent_posts(n: int = 3) -> list[dict]:
    return get_all_posts()[:n]


def get_post(slug: str) -> Optional[dict]:
    path = os.path.join(POSTS_DIR, f"{slug}.md")
    return _load_post(path, render_body=True)


def search_posts(query: str) -> list[dict]:
    q = query.lower().strip()
    if not q:
        return []
    results = []
    for post in get_all_posts():
        if (
            q in post["title"].lower()
            or q in post["excerpt"].lower()
            or any(q in tag.lower() for tag in post["tags"])
        ):
            results.append(post)
    return results


def create_post(slug: str, title: str, date: str, tags: str, body: str) -> None:
    os.makedirs(POSTS_DIR, exist_ok=True)
    tags_clean = ", ".join(t.strip() for t in tags.split(",") if t.strip())
    content = f"---\ntitle: {title}\ndate: {date}\ntags: {tags_clean}\ndraft: false\n---\n\n{body}"
    path = os.path.join(POSTS_DIR, f"{slug}.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
