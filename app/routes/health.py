from datetime import date

import secrets

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.auth import CSRF_COOKIE_NAME, _CSRF_COOKIE_KWARGS, require_admin, require_auth, verify_csrf
from app.models import health as health_model
from app.templates_config import templates

health_model.init_db()

router = APIRouter(prefix="/health")


@router.get("", response_class=HTMLResponse)
async def health_index(request: Request, user: dict = Depends(require_auth)):
    records = health_model.get_records()
    weekly = health_model.get_weekly_averages()
    summary = health_model.get_recent_summary(days=7)
    token = secrets.token_hex(16)
    resp = templates.TemplateResponse("health/index.html", {
        "request": request,
        "user": user,
        "active": "health",
        "records": records,
        "weekly": weekly,
        "summary": summary,
        "today": date.today().isoformat(),
        "csrf_token": token,
    })
    resp.set_cookie(CSRF_COOKIE_NAME, token, **_CSRF_COOKIE_KWARGS)
    return resp


@router.post("/records")
async def add_record(
    request: Request,
    user: dict = Depends(require_admin),
    _csrf: None = Depends(verify_csrf),
    csrf_token: str = Form(...),
    record_date: str = Form(...),
    meals_cooked: int = Form(...),
    exercise_hours: float = Form(...),
    drinks: int = Form(...),
    art_hours: float = Form(...),
    read_hours: float = Form(...),
    tv_hours: float = Form(...),
):
    health_model.upsert_record(record_date, meals_cooked, exercise_hours,
                               drinks, art_hours, read_hours, tv_hours)
    return RedirectResponse("/health", status_code=303)
