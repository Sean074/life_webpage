import base64
import io
import secrets
import sqlite3
import os
from typing import Optional

import pyotp
import qrcode
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse

from app.auth import (
    CSRF_COOKIE_NAME,
    _CSRF_COOKIE_KWARGS,
    create_session,
    generate_backup_codes,
    hash_backup_code,
    hash_password,
    require_admin,
    verify_csrf,
    verify_password,
)
from app.templates_config import templates

router = APIRouter()

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "app.db")


def _totp_qr_b64(username: str, secret: str) -> str:
    uri = pyotp.totp.TOTP(secret).provisioning_uri(name=username, issuer_name="Life")
    qr = qrcode.QRCode(border=1)
    qr.add_data(uri)
    qr.make(fit=True)
    buf = io.BytesIO()
    qr.make_image(fill_color="black", back_color="white").save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def _get_full_user(user_id: int) -> Optional[dict]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT id, username, password_hash, role, totp_secret, totp_enabled FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
    finally:
        conn.close()
    return dict(row) if row else None


def _count_unused_backup_codes(user_id: int) -> int:
    conn = sqlite3.connect(DB_PATH)
    try:
        row = conn.execute(
            "SELECT COUNT(*) FROM backup_codes WHERE user_id = ? AND used_at IS NULL",
            (user_id,),
        ).fetchone()
    finally:
        conn.close()
    return row[0] if row else 0


def _replace_backup_codes(user_id: int) -> list:
    plaintext = generate_backup_codes()
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("DELETE FROM backup_codes WHERE user_id = ?", (user_id,))
        for code in plaintext:
            conn.execute(
                "INSERT INTO backup_codes (user_id, code_hash) VALUES (?, ?)",
                (user_id, hash_backup_code(code)),
            )
        conn.commit()
    finally:
        conn.close()
    return plaintext


def _account_response(request, user, full_user, token, message=None, error=None, pw_error=None, new_backup_codes=None, status_code=200):
    qr_b64 = None
    if full_user["totp_secret"] and not full_user["totp_enabled"]:
        qr_b64 = _totp_qr_b64(user["username"], full_user["totp_secret"])
    resp = templates.TemplateResponse("admin/account.html", {
        "request": request,
        "user": user,
        "active": "account",
        "csrf_token": token,
        "totp_enabled": bool(full_user["totp_enabled"]),
        "totp_pending": bool(full_user["totp_secret"] and not full_user["totp_enabled"]),
        "totp_secret": full_user["totp_secret"],
        "qr_b64": qr_b64,
        "backup_codes_remaining": _count_unused_backup_codes(user["id"]),
        "new_backup_codes": new_backup_codes,
        "message": message,
        "error": error,
        "pw_error": pw_error,
    }, status_code=status_code)
    resp.set_cookie(CSRF_COOKIE_NAME, token, **_CSRF_COOKIE_KWARGS)
    return resp


@router.get("/admin/account")
async def account_get(request: Request, user: dict = Depends(require_admin)):
    full_user = _get_full_user(user["id"])
    token = secrets.token_hex(16)
    return _account_response(request, user, full_user, token)


@router.post("/admin/account/2fa/setup")
async def account_2fa_setup(
    request: Request,
    user: dict = Depends(require_admin),
    _csrf: None = Depends(verify_csrf),
):
    secret = pyotp.random_base32()
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            "UPDATE users SET totp_secret = ?, totp_enabled = 0 WHERE id = ?",
            (secret, user["id"]),
        )
        conn.commit()
    finally:
        conn.close()

    token = secrets.token_hex(16)
    full_user = _get_full_user(user["id"])
    return _account_response(request, user, full_user, token)


@router.post("/admin/account/2fa/confirm")
async def account_2fa_confirm(
    request: Request,
    user: dict = Depends(require_admin),
    code: str = Form(...),
    _csrf: None = Depends(verify_csrf),
):
    full_user = _get_full_user(user["id"])
    if not full_user["totp_secret"]:
        return RedirectResponse("/admin/account", status_code=303)

    if not pyotp.TOTP(full_user["totp_secret"]).verify(code.strip()):
        token = secrets.token_hex(16)
        return _account_response(
            request, user, full_user, token,
            error="! Invalid code. Check your authenticator app and try again.",
            status_code=400,
        )

    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("UPDATE users SET totp_enabled = 1 WHERE id = ?", (user["id"],))
        conn.commit()
    finally:
        conn.close()

    codes = _replace_backup_codes(user["id"])
    token = secrets.token_hex(16)
    full_user = _get_full_user(user["id"])
    return _account_response(
        request, user, full_user, token,
        message="2fa_enabled",
        new_backup_codes=codes,
    )


@router.post("/admin/account/2fa/disable")
async def account_2fa_disable(
    request: Request,
    user: dict = Depends(require_admin),
    password: str = Form(...),
    _csrf: None = Depends(verify_csrf),
):
    full_user = _get_full_user(user["id"])
    if not verify_password(password, full_user["password_hash"]):
        token = secrets.token_hex(16)
        return _account_response(
            request, user, full_user, token,
            error="! Incorrect password.",
            status_code=400,
        )

    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            "UPDATE users SET totp_secret = NULL, totp_enabled = 0 WHERE id = ?",
            (user["id"],),
        )
        conn.execute("DELETE FROM backup_codes WHERE user_id = ?", (user["id"],))
        conn.commit()
    finally:
        conn.close()

    return RedirectResponse("/admin/account?message=2fa_disabled", status_code=303)


@router.post("/admin/account/2fa/recovery-codes/regenerate")
async def account_recovery_codes_regenerate(
    request: Request,
    user: dict = Depends(require_admin),
    password: str = Form(...),
    _csrf: None = Depends(verify_csrf),
):
    full_user = _get_full_user(user["id"])
    if not full_user["totp_enabled"]:
        return RedirectResponse("/admin/account", status_code=303)

    if not verify_password(password, full_user["password_hash"]):
        token = secrets.token_hex(16)
        return _account_response(
            request, user, full_user, token,
            error="! Incorrect password.",
            status_code=400,
        )

    codes = _replace_backup_codes(user["id"])
    token = secrets.token_hex(16)
    return _account_response(
        request, user, full_user, token,
        message="recovery_codes_regenerated",
        new_backup_codes=codes,
    )


@router.post("/admin/account/password")
async def account_password_change(
    request: Request,
    user: dict = Depends(require_admin),
    current_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
    _csrf: None = Depends(verify_csrf),
):
    full_user = _get_full_user(user["id"])

    if not verify_password(current_password, full_user["password_hash"]):
        token = secrets.token_hex(16)
        return _account_response(
            request, user, full_user, token,
            pw_error="! Incorrect current password.",
            status_code=400,
        )

    if new_password != confirm_password:
        token = secrets.token_hex(16)
        return _account_response(
            request, user, full_user, token,
            pw_error="! New password and confirmation do not match.",
            status_code=400,
        )

    if len(new_password) < 8:
        token = secrets.token_hex(16)
        return _account_response(
            request, user, full_user, token,
            pw_error="! New password must be at least 8 characters.",
            status_code=400,
        )

    new_hash = hash_password(new_password)
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            "UPDATE users SET password_hash = ?, session_version = session_version + 1 WHERE id = ?",
            (new_hash, user["id"]),
        )
        conn.commit()
        row = conn.execute(
            "SELECT session_version FROM users WHERE id = ?", (user["id"],)
        ).fetchone()
        new_version = row["session_version"]
    finally:
        conn.close()

    response = RedirectResponse("/admin/account?message=password_changed", status_code=303)
    create_session(response, user["id"], new_version)
    return response
