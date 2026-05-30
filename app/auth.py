import os
import secrets
import sqlite3
from pathlib import Path
from typing import Optional

import bcrypt
from fastapi import Depends, Form, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from itsdangerous import BadSignature, SignatureExpired, TimestampSigner

DB_PATH = Path(__file__).parent.parent / "data" / "library.db"
COOKIE_NAME = "session"
SESSION_MAX_AGE = 60 * 60 * 24 * 7  # 7 days


def _signer() -> TimestampSigner:
    secret = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    if secret == "dev-secret-change-me":
        import warnings
        warnings.warn("SECRET_KEY is unset — sessions are insecure", stacklevel=2)
    return TimestampSigner(secret)


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_session(response: Response, user_id: int) -> None:
    token = _signer().sign(str(user_id)).decode()
    secure = os.environ.get("HTTPS_ONLY", "false").lower() == "true"
    response.set_cookie(
        COOKIE_NAME,
        token,
        max_age=SESSION_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=secure,
    )


def clear_session(response: Response) -> None:
    response.delete_cookie(COOKIE_NAME)


def get_current_user(request: Request) -> Optional[dict]:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    try:
        data = _signer().unsign(token, max_age=SESSION_MAX_AGE)
        user_id = int(data)
    except (BadSignature, SignatureExpired, ValueError):
        return None

    conn = _connect()
    try:
        row = conn.execute(
            "SELECT id, username, role FROM users WHERE id = ?", (user_id,)
        ).fetchone()
    finally:
        conn.close()

    if not row:
        return None
    return {"id": row["id"], "username": row["username"], "role": row["role"]}


def require_auth(request: Request) -> dict:
    user = get_current_user(request)
    if not user:
        raise HTTPException(
            status_code=307,
            detail="Not authenticated",
            headers={"Location": "/login"},
        )
    return user


def require_admin(user: dict = Depends(require_auth)) -> dict:
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


PENDING_2FA_COOKIE = "pending_2fa"
PENDING_2FA_MAX_AGE = 300  # 5 minutes


def create_pending_2fa(response: Response, user_id: int) -> None:
    token = _signer().sign(f"2fa:{user_id}").decode()
    secure = os.environ.get("HTTPS_ONLY", "false").lower() == "true"
    response.set_cookie(
        PENDING_2FA_COOKIE,
        token,
        max_age=PENDING_2FA_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=secure,
    )


def verify_pending_2fa(request: Request) -> Optional[int]:
    token = request.cookies.get(PENDING_2FA_COOKIE)
    if not token:
        return None
    try:
        data = _signer().unsign(token, max_age=PENDING_2FA_MAX_AGE).decode()
        if not data.startswith("2fa:"):
            return None
        return int(data[4:])
    except (BadSignature, SignatureExpired, ValueError):
        return None


CSRF_COOKIE_NAME = "csrf_token"
_CSRF_COOKIE_KWARGS: dict = {"httponly": False, "samesite": "lax"}


def issue_csrf(response: Response) -> str:
    token = secrets.token_hex(16)
    response.set_cookie(CSRF_COOKIE_NAME, token, **_CSRF_COOKIE_KWARGS)
    return token


def verify_csrf(request: Request, csrf_token: str = Form(...)) -> None:
    cookie_token = request.cookies.get(CSRF_COOKIE_NAME, "")
    if not secrets.compare_digest(csrf_token, cookie_token):
        raise HTTPException(status_code=400, detail="Invalid CSRF token")
