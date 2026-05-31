import csv
import logging
from datetime import date, timedelta

import secrets

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse

from app.auth import CSRF_COOKIE_NAME, _CSRF_COOKIE_KWARGS, require_admin, require_auth, verify_csrf
from app.models import expenses as expenses_model
from app.services import expenses as expenses_svc
from app.templates_config import templates

router = APIRouter(prefix="/expenses")


def _month_label(months_ago: int) -> str:
    today = date.today()
    # Step back by replacing day=1 and subtracting months
    m = today.month - months_ago
    y = today.year + (m - 1) // 12
    m = ((m - 1) % 12) + 1
    return date(y, m, 1).strftime("%b %Y")


@router.get("", response_class=HTMLResponse)
async def expenses_index(request: Request, user: dict = Depends(require_auth)):
    token = secrets.token_hex(16)
    resp = templates.TemplateResponse(request, "expenses/index.html", {
        "user": user,
        "active": "expenses",
        "csrf_token": token,
        "today": date.today().isoformat(),
        "transactions": expenses_model.get_transactions(),
        "categories": expenses_model.get_categories(),
        "summary": expenses_model.get_summary(),
        "month_labels": [_month_label(i) for i in range(3)],
        "monthly": expenses_model.get_monthly_totals(),
        "monthly_by_cat": expenses_model.get_monthly_by_category(),
        "cat_totals": expenses_model.get_category_totals(),
        "bank_options": list(expenses_svc.PARSERS.keys()),
    })
    resp.set_cookie(CSRF_COOKIE_NAME, token, **_CSRF_COOKIE_KWARGS)
    return resp


@router.post("/transactions")
async def add_transaction(
    request: Request,
    user: dict = Depends(require_admin),
    _csrf: None = Depends(verify_csrf),
    csrf_token: str = Form(...),
    txn_date: str = Form(...),
    amount: float = Form(...),
    description: str = Form(""),
    category: str = Form("other"),
    account: str = Form(""),
    type_: str = Form(..., alias="type"),
):
    expenses_model.add_transaction(txn_date, amount, description, category, account, type_)
    return RedirectResponse("/expenses", status_code=303)


@router.post("/transactions/{txn_id}/edit")
async def edit_transaction(
    request: Request,
    txn_id: int,
    user: dict = Depends(require_admin),
    _csrf: None = Depends(verify_csrf),
    csrf_token: str = Form(...),
    txn_date: str = Form(...),
    amount: float = Form(...),
    description: str = Form(""),
    category: str = Form("other"),
    account: str = Form(""),
    type_: str = Form(..., alias="type"),
):
    expenses_model.update_transaction(txn_id, txn_date, amount, description, category, account, type_)
    return RedirectResponse("/expenses", status_code=303)


@router.post("/transactions/{txn_id}/delete")
async def delete_transaction(
    request: Request,
    txn_id: int,
    user: dict = Depends(require_admin),
    _csrf: None = Depends(verify_csrf),
    csrf_token: str = Form(...),
):
    expenses_model.delete_transaction(txn_id)
    return RedirectResponse("/expenses", status_code=303)


@router.post("/import")
async def import_csv(
    request: Request,
    user: dict = Depends(require_admin),
    _csrf: None = Depends(verify_csrf),
    csrf_token: str = Form(...),
    bank: str = Form(...),
    file: UploadFile = File(...),
):
    contents = await file.read()
    try:
        transactions = expenses_svc.parse_csv(bank, contents)
        expenses_svc.bulk_import(transactions)
    except (ValueError, KeyError, csv.Error, UnicodeDecodeError) as exc:
        logging.getLogger(__name__).error("CSV import error: %s", exc)
        return HTMLResponse("Import failed: check file format.", status_code=400)
    return RedirectResponse("/expenses", status_code=303)


@router.post("/categories")
async def add_category(
    request: Request,
    user: dict = Depends(require_admin),
    _csrf: None = Depends(verify_csrf),
    csrf_token: str = Form(...),
    name: str = Form(...),
):
    expenses_model.add_category(name.strip().lower())
    return RedirectResponse("/expenses", status_code=303)


@router.post("/categories/{cat_id}/delete")
async def delete_category(
    request: Request,
    cat_id: int,
    user: dict = Depends(require_admin),
    _csrf: None = Depends(verify_csrf),
    csrf_token: str = Form(...),
):
    expenses_model.delete_category(cat_id)
    return RedirectResponse("/expenses", status_code=303)
