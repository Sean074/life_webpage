import os
import secrets
import sqlite3
import time
from collections import defaultdict
from typing import Optional

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse

import pyotp

from app.auth import (
    CSRF_COOKIE_NAME,
    PENDING_2FA_COOKIE,
    clear_session,
    create_pending_2fa,
    create_session,
    get_current_user,
    verify_backup_code,
    verify_csrf,
    verify_password,
    verify_pending_2fa,
)
from app.templates_config import templates

router = APIRouter()

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "app.db")

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
            "SELECT id, username, password_hash, role, totp_secret, totp_enabled, session_version FROM users WHERE username = ?",
            (username,),
        ).fetchone()
    finally:
        conn.close()
    if not row:
        return None
    return dict(row)


def _get_user_by_id(user_id: int) -> Optional[dict]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT id, username, password_hash, role, totp_secret, totp_enabled, session_version FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
    finally:
        conn.close()
    if not row:
        return None
    return dict(row)


@router.get("/login")
async def login_get(request: Request):
    if get_current_user(request):
        return RedirectResponse("/", status_code=303)
    token = secrets.token_hex(16)
    resp = templates.TemplateResponse(request, "login.html", {
        "user": None,
        "active": "login",
        "csrf_token": token,
        "error": None,
    })
    resp.set_cookie(CSRF_COOKIE_NAME, token, httponly=False, samesite="lax")
    return resp


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
        new_token = secrets.token_hex(16)
        resp = templates.TemplateResponse(request, "login.html", {
            "user": None,
            "active": "login",
            "csrf_token": new_token,
            "error": "Too many failed attempts. Try again in a minute.",
        }, status_code=429)
        resp.set_cookie(CSRF_COOKIE_NAME, new_token, httponly=False, samesite="lax")
        return resp

    user = _get_user_by_username(username)
    if not user or not verify_password(password, user["password_hash"]):
        _record_failure(ip)
        new_token = secrets.token_hex(16)
        resp = templates.TemplateResponse(request, "login.html", {
            "user": None,
            "active": "login",
            "csrf_token": new_token,
            "error": "Invalid username or password.",
        }, status_code=401)
        resp.set_cookie(CSRF_COOKIE_NAME, new_token, httponly=False, samesite="lax")
        return resp

    if user["totp_enabled"]:
        response = RedirectResponse("/login/2fa", status_code=303)
        create_pending_2fa(response, user["id"])
        return response

    response = RedirectResponse("/", status_code=303)
    create_session(response, user["id"], user["session_version"])
    response.delete_cookie(CSRF_COOKIE_NAME)
    return response


@router.get("/login/2fa")
async def login_2fa_get(request: Request):
    if not verify_pending_2fa(request):
        return RedirectResponse("/login", status_code=303)
    token = secrets.token_hex(16)
    resp = templates.TemplateResponse(request, "login_totp.html", {
        "user": None,
        "active": "login",
        "csrf_token": token,
        "error": None,
    })
    resp.set_cookie(CSRF_COOKIE_NAME, token, httponly=False, samesite="lax")
    return resp


@router.post("/login/2fa")
async def login_2fa_post(
    request: Request,
    code: str = Form(...),
    csrf_token: str = Form(...),
    _csrf: None = Depends(verify_csrf),
):
    ip = request.headers.get("X-Real-IP") or request.client.host

    if _is_rate_limited(ip):
        new_token = secrets.token_hex(16)
        resp = templates.TemplateResponse(request, "login_totp.html", {
            "user": None,
            "active": "login",
            "csrf_token": new_token,
            "error": "Too many failed attempts. Try again in a minute.",
        }, status_code=429)
        resp.set_cookie(CSRF_COOKIE_NAME, new_token, httponly=False, samesite="lax")
        return resp

    user_id = verify_pending_2fa(request)
    if not user_id:
        return RedirectResponse("/login", status_code=303)

    user = _get_user_by_id(user_id)
    if not user or not user["totp_enabled"] or not user["totp_secret"]:
        return RedirectResponse("/login", status_code=303)

    if not pyotp.TOTP(user["totp_secret"]).verify(code.strip()):
        _record_failure(ip)
        new_token = secrets.token_hex(16)
        resp = templates.TemplateResponse(request, "login_totp.html", {
            "user": None,
            "active": "login",
            "csrf_token": new_token,
            "error": "! Invalid code. Try again.",
        }, status_code=401)
        resp.set_cookie(CSRF_COOKIE_NAME, new_token, httponly=False, samesite="lax")
        return resp

    response = RedirectResponse("/", status_code=303)
    create_session(response, user["id"], user["session_version"])
    response.delete_cookie(PENDING_2FA_COOKIE)
    response.delete_cookie(CSRF_COOKIE_NAME)
    return response


@router.get("/login/2fa/recovery")
async def login_recovery_get(request: Request):
    if not verify_pending_2fa(request):
        return RedirectResponse("/login", status_code=303)
    token = secrets.token_hex(16)
    resp = templates.TemplateResponse(request, "login_recovery.html", {
        "user": None,
        "active": "login",
        "csrf_token": token,
        "error": None,
    })
    resp.set_cookie(CSRF_COOKIE_NAME, token, httponly=False, samesite="lax")
    return resp


@router.post("/login/2fa/recovery")
async def login_recovery_post(
    request: Request,
    code: str = Form(...),
    csrf_token: str = Form(...),
    _csrf: None = Depends(verify_csrf),
):
    ip = request.headers.get("X-Real-IP") or request.client.host

    if _is_rate_limited(ip):
        new_token = secrets.token_hex(16)
        resp = templates.TemplateResponse(request, "login_recovery.html", {
            "user": None,
            "active": "login",
            "csrf_token": new_token,
            "error": "Too many failed attempts. Try again in a minute.",
        }, status_code=429)
        resp.set_cookie(CSRF_COOKIE_NAME, new_token, httponly=False, samesite="lax")
        return resp

    user_id = verify_pending_2fa(request)
    if not user_id:
        return RedirectResponse("/login", status_code=303)

    user = _get_user_by_id(user_id)
    if not user or not user["totp_enabled"]:
        return RedirectResponse("/login", status_code=303)

    matched_id = None
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT id, code_hash FROM backup_codes WHERE user_id = ? AND used_at IS NULL",
            (user_id,),
        ).fetchall()
        for row in rows:
            if verify_backup_code(code, row["code_hash"]):
                matched_id = row["id"]
                break
        if matched_id is not None:
            conn.execute(
                "UPDATE backup_codes SET used_at = CURRENT_TIMESTAMP WHERE id = ?",
                (matched_id,),
            )
            conn.commit()
    finally:
        conn.close()

    if matched_id is None:
        _record_failure(ip)
        new_token = secrets.token_hex(16)
        resp = templates.TemplateResponse(request, "login_recovery.html", {
            "user": None,
            "active": "login",
            "csrf_token": new_token,
            "error": "! Invalid backup code.",
        }, status_code=401)
        resp.set_cookie(CSRF_COOKIE_NAME, new_token, httponly=False, samesite="lax")
        return resp

    response = RedirectResponse("/", status_code=303)
    create_session(response, user["id"], user["session_version"])
    response.delete_cookie(PENDING_2FA_COOKIE)
    response.delete_cookie(CSRF_COOKIE_NAME)
    return response


@router.get("/logout")
async def logout(request: Request):
    response = RedirectResponse("/", status_code=303)
    clear_session(response)
    return response
