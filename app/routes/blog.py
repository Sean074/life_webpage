import re
import secrets
from datetime import date

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.auth import (
    CSRF_COOKIE_NAME,
    _CSRF_COOKIE_KWARGS,
    get_current_user,
    require_admin,
    require_auth,
    verify_csrf,
)
from app.services import blog as blog_svc
from app.templates_config import templates

router = APIRouter()


@router.get("/blog", response_class=HTMLResponse)
async def blog_index(request: Request):
    user = get_current_user(request)
    q_param = request.query_params.get("q")  # None if not present, "" if ?q=
    if q_param is None:
        posts = blog_svc.get_recent_posts(3)
        query = None
    elif q_param.strip():
        posts = blog_svc.search_posts(q_param)
        query = q_param
    else:
        posts = blog_svc.get_all_posts()
        query = ""
    return templates.TemplateResponse("blog/index.html", {
        "request": request,
        "user": user,
        "active": "blog",
        "posts": posts,
        "query": query,
    })


@router.get("/blog/new", response_class=HTMLResponse)
async def blog_new_get(request: Request, user=Depends(require_auth)):
    token = secrets.token_hex(16)
    resp = templates.TemplateResponse("blog/new.html", {
        "request": request,
        "user": user,
        "active": "blog",
        "csrf_token": token,
        "errors": {},
    })
    resp.set_cookie(CSRF_COOKIE_NAME, token, **_CSRF_COOKIE_KWARGS)
    return resp


@router.post("/blog/new")
async def blog_new_post(
    request: Request,
    user=Depends(require_admin),
    _csrf: None = Depends(verify_csrf),
    title: str = Form(...),
    slug: str = Form(...),
    date_str: str = Form(...),
    tags: str = Form(""),
    body: str = Form(...),
    csrf_token: str = Form(...),
):
    errors: dict = {}
    slug_clean = re.sub(r"[^a-z0-9-]", "", slug.lower().replace(" ", "-"))
    if not title.strip():
        errors["title"] = "Title is required."
    if not slug_clean:
        errors["slug"] = "Slug is required and must contain letters or numbers."
    if not body.strip():
        errors["body"] = "Post body is required."

    if errors:
        new_csrf = secrets.token_hex(16)
        resp = templates.TemplateResponse("blog/new.html", {
            "request": request,
            "user": user,
            "active": "blog",
            "csrf_token": new_csrf,
            "errors": errors,
            "values": {"title": title, "slug": slug, "date": date_str, "tags": tags, "body": body},
        }, status_code=422)
        resp.set_cookie(CSRF_COOKIE_NAME, new_csrf, **_CSRF_COOKIE_KWARGS)
        return resp

    post_date = date_str or str(date.today())
    blog_svc.create_post(slug_clean, title.strip(), post_date, tags, body.strip())
    return RedirectResponse(f"/blog/{slug_clean}", status_code=303)


@router.get("/blog/{slug}/edit", response_class=HTMLResponse)
async def blog_edit_get(slug: str, request: Request, user=Depends(require_admin)):
    post = blog_svc.get_post_raw(slug)
    if post is None:
        return RedirectResponse("/blog", status_code=303)
    token = secrets.token_hex(16)
    resp = templates.TemplateResponse("blog/edit.html", {
        "request": request,
        "user": user,
        "active": "blog",
        "post": post,
        "csrf_token": token,
        "errors": {},
    })
    resp.set_cookie(CSRF_COOKIE_NAME, token, **_CSRF_COOKIE_KWARGS)
    return resp


@router.post("/blog/{slug}/edit")
async def blog_edit_post(
    slug: str,
    request: Request,
    user=Depends(require_admin),
    _csrf: None = Depends(verify_csrf),
    title: str = Form(...),
    date_str: str = Form(...),
    tags: str = Form(""),
    body: str = Form(...),
    draft: str = Form(""),
    csrf_token: str = Form(...),
):
    errors: dict = {}
    if not title.strip():
        errors["title"] = "Title is required."
    if not body.strip():
        errors["body"] = "Post body is required."

    if errors:
        new_csrf = secrets.token_hex(16)
        post = blog_svc.get_post_raw(slug)
        resp = templates.TemplateResponse("blog/edit.html", {
            "request": request,
            "user": user,
            "active": "blog",
            "post": post,
            "csrf_token": new_csrf,
            "errors": errors,
            "values": {"title": title, "date": date_str, "tags": tags, "body": body, "draft": bool(draft)},
        }, status_code=422)
        resp.set_cookie(CSRF_COOKIE_NAME, new_csrf, **_CSRF_COOKIE_KWARGS)
        return resp

    blog_svc.update_post(slug, title.strip(), date_str, tags, body.strip(), draft=bool(draft))
    return RedirectResponse(f"/blog/{slug}", status_code=303)


@router.post("/blog/{slug}/delete")
async def blog_delete_post(
    slug: str,
    request: Request,
    user=Depends(require_admin),
    _csrf: None = Depends(verify_csrf),
    csrf_token: str = Form(...),
):
    blog_svc.delete_post(slug)
    return RedirectResponse("/blog", status_code=303)


@router.get("/blog/{slug}", response_class=HTMLResponse)
async def blog_post(slug: str, request: Request):
    user = get_current_user(request)
    post = blog_svc.get_post(slug)
    if post is None:
        return templates.TemplateResponse("blog/post.html", {
            "request": request,
            "user": user,
            "active": "blog",
            "post": None,
        }, status_code=404)
    token = secrets.token_hex(16)
    resp = templates.TemplateResponse("blog/post.html", {
        "request": request,
        "user": user,
        "active": "blog",
        "post": post,
        "csrf_token": token,
    })
    resp.set_cookie(CSRF_COOKIE_NAME, token, **_CSRF_COOKIE_KWARGS)
    return resp
