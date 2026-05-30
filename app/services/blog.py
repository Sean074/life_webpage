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


_ALLOWED_TAGS = {
    "p", "br", "hr", "blockquote", "pre", "code",
    "h1", "h2", "h3", "h4", "h5", "h6",
    "ul", "ol", "li",
    "strong", "em", "del", "a", "img",
    "table", "thead", "tbody", "tr", "th", "td",
}
_SAFE_PROTOCOLS = ("http://", "https://", "mailto:", "/", "#")


def _allow_attr(tag: str, name: str, value: str) -> bool:
    if name in ("href", "src"):
        return value.lower().lstrip().startswith(_SAFE_PROTOCOLS)
    return name in ("alt", "title")


def _render_markdown(text: str) -> str:
    import bleach
    import markdown as md
    html = md.markdown(text, extensions=["fenced_code", "tables"])
    return bleach.clean(html, tags=_ALLOWED_TAGS, attributes=_allow_attr, strip=True)


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
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", slug):
        return None
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
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", slug):
        raise ValueError(f"Invalid slug: {slug!r}")
    os.makedirs(POSTS_DIR, exist_ok=True)
    tags_clean = ", ".join(t.strip() for t in tags.split(",") if t.strip())
    content = f"---\ntitle: {title}\ndate: {date}\ntags: {tags_clean}\ndraft: false\n---\n\n{body}"
    path = os.path.join(POSTS_DIR, f"{slug}.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def get_post_raw(slug: str) -> Optional[dict]:
    """Load post for editing — includes drafts, returns raw (un-rendered) body."""
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", slug):
        return None
    path = os.path.join(POSTS_DIR, f"{slug}.md")
    try:
        with open(path, encoding="utf-8") as f:
            raw = f.read()
    except OSError:
        return None
    fm, body = _parse_frontmatter(raw)
    return {
        "slug": slug,
        "title": fm.get("title", slug),
        "date": fm.get("date", ""),
        "tags": fm.get("tags", ""),
        "draft": fm.get("draft", "false").lower() == "true",
        "body": body,
    }


def update_post(slug: str, title: str, date: str, tags: str, body: str, draft: bool) -> None:
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", slug):
        raise ValueError(f"Invalid slug: {slug!r}")
    path = os.path.join(POSTS_DIR, f"{slug}.md")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Post not found: {slug!r}")
    tags_clean = ", ".join(t.strip() for t in tags.split(",") if t.strip())
    draft_val = "true" if draft else "false"
    content = f"---\ntitle: {title}\ndate: {date}\ntags: {tags_clean}\ndraft: {draft_val}\n---\n\n{body}"
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def delete_post(slug: str) -> None:
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", slug):
        raise ValueError(f"Invalid slug: {slug!r}")
    path = os.path.join(POSTS_DIR, f"{slug}.md")
    if os.path.exists(path):
        os.remove(path)
