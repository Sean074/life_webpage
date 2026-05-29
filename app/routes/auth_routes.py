import os
import sqlite3
import time
from collections import defaultdict
from typing import Optional

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse

from app.auth import (
    CSRF_COOKIE_NAME,
    clear_session,
    create_session,
    get_current_user,
    issue_csrf,
    verify_csrf,
    verify_password,
)
from app.templates_config import templates

router = APIRouter()

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "library.db")

# rate limiting: {ip: [timestamp, ...]}
_failures: dict = defaultdict(list)
_RATE_WINDOW = 60
_RATE_LIMIT = 5


def _is_rate_limited(ip: str) -> bool:
    now = time.time()
    _failures[ip] = [t for t in _failures[ip] if now - t < _RATE_WINDOW]
    return len(_failures[ip]) >= _RATE_LIMIT


def _record_failure(ip: str) -> None:
    _failures[ip].append(time.time())


def _get_user_by_username(username: str) -> Optional[dict]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT id, username, password_hash, role FROM users WHERE username = ?",
            (username,),
        ).fetchone()
    finally:
        conn.close()
    if not row:
        return None
    return dict(row)


@router.get("/login")
async def login_get(request: Request, csrf_token: str = Depends(issue_csrf)):
    if get_current_user(request):
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse("login.html", {
        "request": request,
        "user": None,
        "active": "login",
        "csrf_token": csrf_token,
        "error": None,
    })


@router.post("/login")
async def login_post(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    csrf_token: str = Form(...),
    _csrf: None = Depends(verify_csrf),
):
    ip = request.headers.get("X-Real-IP") or request.client.host

    if _is_rate_limited(ip):
        return templates.TemplateResponse("login.html", {
            "request": request,
            "user": None,
            "active": "login",
            "csrf_token": csrf_token,
            "error": "Too many failed attempts. Try again in a minute.",
        }, status_code=429)

    user = _get_user_by_username(username)
    if not user or not verify_password(password, user["password_hash"]):
        _record_failure(ip)
        return templates.TemplateResponse("login.html", {
            "request": request,
            "user": None,
            "active": "login",
            "csrf_token": csrf_token,
            "error": "Invalid username or password.",
        }, status_code=401)

    response = RedirectResponse("/", status_code=303)
    create_session(response, user["id"])
    response.delete_cookie(CSRF_COOKIE_NAME)
    return response


@router.get("/logout")
async def logout(request: Request):
    response = RedirectResponse("/", status_code=303)
    clear_session(response)
    return response
