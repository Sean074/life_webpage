import secrets
from datetime import date

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.auth import require_admin, require_auth
from app.models import health as health_model
from app.templates_config import templates

health_model.init_db()

router = APIRouter(prefix="/health")


@router.get("", response_class=HTMLResponse)
async def health_index(request: Request, user: dict = Depends(require_auth)):
    records = health_model.get_records()
    weekly = health_model.get_weekly_averages()
    summary = health_model.get_recent_summary(days=7)

    csrf_token = secrets.token_hex(16)
    response = templates.TemplateResponse("health/index.html", {
        "request": request,
        "user": user,
        "active": "health",
        "records": records,
        "weekly": weekly,
        "summary": summary,
        "today": date.today().isoformat(),
        "csrf_token": csrf_token,
    })
    response.set_cookie("csrf_token", csrf_token, httponly=False, samesite="lax")
    return response


@router.post("/records")
async def add_record(
    request: Request,
    user: dict = Depends(require_admin),
    csrf_token: str = Form(...),
    record_date: str = Form(...),
    meals_cooked: int = Form(...),
    exercise_hours: float = Form(...),
    drinks: int = Form(...),
    art_hours: float = Form(...),
    read_hours: float = Form(...),
    tv_hours: float = Form(...),
):
    cookie_token = request.cookies.get("csrf_token", "")
    if not secrets.compare_digest(csrf_token, cookie_token):
        return HTMLResponse("Invalid CSRF token", status_code=400)
    health_model.upsert_record(record_date, meals_cooked, exercise_hours,
                               drinks, art_hours, read_hours, tv_hours)
    return RedirectResponse("/health", status_code=303)
