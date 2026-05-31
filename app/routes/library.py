import secrets

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse

from app.auth import CSRF_COOKIE_NAME, _CSRF_COOKIE_KWARGS, require_admin, require_auth, verify_csrf
from app.templates_config import templates
from app.models.library import (
    LIBRARY_ROOT,
    all_disciplines,
    all_tags,
    create_item,
    get_all_items,
    get_incomplete_items,
    get_item,
    get_untracked_files,
    update_item,
)

router = APIRouter(prefix="/library")


@router.get("")
async def index(request: Request, user: dict = Depends(require_auth)):
    return templates.TemplateResponse(request, "library/index.html", {
        "user": user,
        "active": "library",
    })


@router.get("/search")
async def search(
    request: Request,
    q: str = "",
    discipline: str = "",
    tag: str = "",
    rating: str = "",
    user: dict = Depends(require_auth),
):
    items = get_all_items(
        query=q or None,
        discipline=discipline or None,
        tag=tag or None,
        rating=int(rating) if rating else None,
    )
    return templates.TemplateResponse(request, "library/search.html", {
        "user": user,
        "active": "library",
        "items": items,
        "q": q,
        "discipline": discipline,
        "tag": tag,
        "rating": rating,
        "disciplines": all_disciplines(),
        "tags": all_tags(),
    })


@router.get("/sync")
async def sync_get(request: Request, user: dict = Depends(require_admin)):
    untracked = get_untracked_files()
    token = secrets.token_hex(16)
    resp = templates.TemplateResponse(request, "library/sync.html", {
        "user": user,
        "active": "library",
        "untracked": untracked,
        "csrf_token": token,
    })
    resp.set_cookie(CSRF_COOKIE_NAME, token, **_CSRF_COOKIE_KWARGS)
    return resp


@router.post("/sync")
async def sync_post(
    request: Request,
    user: dict = Depends(require_admin),
    _csrf: None = Depends(verify_csrf),
    csrf_token: str = Form(...),
):
    for rel_path in get_untracked_files():
        pdf = LIBRARY_ROOT / rel_path
        discipline = pdf.parent.name if pdf.parent != LIBRARY_ROOT else None
        title = pdf.stem.replace("_", " ").replace("-", " ")
        create_item({"title": title, "discipline": discipline, "file_path": rel_path})
    return RedirectResponse("/library/sync", status_code=303)


@router.get("/review")
async def review(request: Request, user: dict = Depends(require_auth)):
    items = get_all_items()
    incomplete_ids = {i["id"] for i in get_incomplete_items()}
    return templates.TemplateResponse(request, "library/review.html", {
        "user": user,
        "active": "library",
        "items": items,
        "incomplete_ids": incomplete_ids,
    })


@router.get("/items/{item_id}/edit")
async def edit_get(request: Request, item_id: int, user: dict = Depends(require_admin)):
    item = get_item(item_id)
    if not item:
        return RedirectResponse("/library/review", status_code=303)
    token = secrets.token_hex(16)
    resp = templates.TemplateResponse(request, "library/edit.html", {
        "user": user,
        "active": "library",
        "item": item,
        "disciplines": all_disciplines(),
        "csrf_token": token,
    })
    resp.set_cookie(CSRF_COOKIE_NAME, token, **_CSRF_COOKIE_KWARGS)
    return resp


@router.post("/items/{item_id}/edit")
async def edit_post(
    request: Request,
    item_id: int,
    user: dict = Depends(require_admin),
    _csrf: None = Depends(verify_csrf),
    csrf_token: str = Form(...),
    title: str = Form(...),
    author: str = Form(""),
    ref_number: str = Form(""),
    discipline: str = Form(""),
    description: str = Form(""),
    comment: str = Form(""),
    rating: str = Form(""),
    tags: str = Form(""),
):
    update_item(item_id, {
        "title": title,
        "author": author or None,
        "ref_number": ref_number or None,
        "discipline": discipline or None,
        "description": description or None,
        "comment": comment or None,
        "rating": int(rating) if rating else None,
        "tags": [t.strip() for t in tags.split(",") if t.strip()],
    })
    return RedirectResponse("/library/review", status_code=303)
