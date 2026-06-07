import secrets
from datetime import date, timedelta

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.auth import CSRF_COOKIE_NAME, _CSRF_COOKIE_KWARGS, require_admin, require_auth, verify_csrf
from app.models import expenses as expenses_model
from app.models import health as health_model
from app.templates_config import templates

router = APIRouter(prefix="/today")


def _week_bounds(today: date) -> tuple[date, date]:
    days_since_sat = (today.weekday() - 5) % 7
    week_start = today - timedelta(days=days_since_sat)
    week_end = week_start + timedelta(days=6)
    return week_start, week_end


def _build_week_tracker(today: date, logged_dates: list[str]) -> list[dict]:
    logged_set = set(logged_dates)
    days = []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        days.append({
            "date": d.isoformat(),
            "label": d.strftime("%a"),
            "logged": d.isoformat() in logged_set,
            "is_today": d == today,
        })
    return days


@router.get("", response_class=HTMLResponse)
async def today_index(request: Request, user: dict = Depends(require_auth)):
    today = date.today()
    week_start, week_end = _week_bounds(today)

    today_total = expenses_model.get_today_total(today.isoformat())
    week_total = expenses_model.get_week_total(week_start.isoformat(), week_end.isoformat())
    month_total = expenses_model.get_month_total(today.year, today.month)

    logged_dates = health_model.get_logged_dates_last_7(today.isoformat())
    week_tracker = _build_week_tracker(today, logged_dates)

    categories = expenses_model.get_categories()

    token = secrets.token_hex(16)
    resp = templates.TemplateResponse(request, "today/index.html", {
        "user": user,
        "active": "today",
        "csrf_token": token,
        "today": today.isoformat(),
        "today_total": today_total,
        "week_total": week_total,
        "month_total": month_total,
        "week_label": f"{week_start.strftime('%b %-d')} – {week_end.strftime('%b %-d')}",
        "month_label": today.strftime("%B %Y"),
        "week_tracker": week_tracker,
        "categories": categories,
    })
    resp.set_cookie(CSRF_COOKIE_NAME, token, **_CSRF_COOKIE_KWARGS)
    return resp


@router.post("/expense")
async def add_expense(
    request: Request,
    user: dict = Depends(require_admin),
    _csrf: None = Depends(verify_csrf),
    csrf_token: str = Form(...),
    txn_date: str = Form(...),
    amount: float = Form(...),
    description: str = Form(""),
    category: str = Form("other"),
    account: str = Form(""),
):
    expenses_model.add_transaction(txn_date, amount, description, category, account, "debit")
    return RedirectResponse("/today", status_code=303)


@router.post("/health")
async def log_health(
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
    return RedirectResponse("/today", status_code=303)
