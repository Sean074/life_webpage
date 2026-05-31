from datetime import date

import secrets

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.auth import CSRF_COOKIE_NAME, _CSRF_COOKIE_KWARGS, require_admin, require_auth, verify_csrf
from app.models import wealth as wealth_model
from app.services import wealth as wealth_svc
from app.templates_config import templates

router = APIRouter(prefix="/wealth")

ACCOUNT_TYPES = ["savings", "investment", "retirement", "property", "liability"]


@router.get("", response_class=HTMLResponse)
async def wealth_index(request: Request, user: dict = Depends(require_auth)):
    accounts = wealth_model.get_accounts()
    params = wealth_model.get_projection_params()
    history = wealth_svc.load_history()
    net_worth = wealth_svc.current_net_worth(accounts)
    projection = wealth_svc.run_projection(params, net_worth)
    backward_projection = wealth_svc.run_backward_projection(params, net_worth)
    token = secrets.token_hex(16)
    resp = templates.TemplateResponse(request, "wealth/index.html", {
        "user": user,
        "active": "wealth",
        "accounts": accounts,
        "params": params,
        "history": history,
        "net_worth": net_worth,
        "projection": projection,
        "backward_projection": backward_projection,
        "account_types": ACCOUNT_TYPES,
        "csrf_token": token,
        "today": date.today().isoformat(),
    })
    resp.set_cookie(CSRF_COOKIE_NAME, token, **_CSRF_COOKIE_KWARGS)
    return resp


@router.post("/accounts/bulk-update")
async def bulk_update_accounts(
    request: Request,
    user: dict = Depends(require_admin),
    _csrf: None = Depends(verify_csrf),
    csrf_token: str = Form(...),
    last_updated: str = Form(None),
):
    if last_updated is None:
        last_updated = date.today().isoformat()
    form = await request.form()
    accounts = wealth_model.get_accounts()
    for acct in accounts:
        raw = form.get(f"balance_{acct['id']}")
        if raw is not None:
            try:
                wealth_model.upsert_account(
                    acct["name"], float(raw), acct["type"],
                    acct["institution"], last_updated, account_id=acct["id"],
                )
            except ValueError:
                pass
    return RedirectResponse("/wealth", status_code=303)


@router.post("/accounts")
async def add_account(
    request: Request,
    user: dict = Depends(require_admin),
    _csrf: None = Depends(verify_csrf),
    csrf_token: str = Form(...),
    name: str = Form(...),
    balance: float = Form(...),
    type_: str = Form(..., alias="type"),
    institution: str = Form(""),
    last_updated: str = Form(...),
):
    wealth_model.upsert_account(name, balance, type_, institution, last_updated)
    return RedirectResponse("/wealth", status_code=303)


@router.post("/accounts/{account_id}/edit")
async def edit_account(
    request: Request,
    account_id: int,
    user: dict = Depends(require_admin),
    _csrf: None = Depends(verify_csrf),
    csrf_token: str = Form(...),
    name: str = Form(...),
    balance: float = Form(...),
    type_: str = Form(..., alias="type"),
    institution: str = Form(""),
    last_updated: str = Form(...),
):
    wealth_model.upsert_account(name, balance, type_, institution, last_updated, account_id=account_id)
    return RedirectResponse("/wealth", status_code=303)


@router.post("/accounts/{account_id}/delete")
async def delete_account(
    request: Request,
    account_id: int,
    user: dict = Depends(require_admin),
    _csrf: None = Depends(verify_csrf),
    csrf_token: str = Form(...),
):
    wealth_model.delete_account(account_id)
    return RedirectResponse("/wealth", status_code=303)


@router.post("/projection")
async def update_projection(
    request: Request,
    user: dict = Depends(require_admin),
    _csrf: None = Depends(verify_csrf),
    csrf_token: str = Form(...),
    annual_salary: float = Form(...),
    annual_spending: float = Form(...),
    salary_growth_rate: float = Form(...),
    inflation_rate: float = Form(...),
    investment_return_rate: float = Form(...),
    retirement_year: int = Form(...),
    retirement_spending_adj: float = Form(...),
    horizon_year: int = Form(...),
):
    wealth_model.update_projection_params({
        "annual_salary": annual_salary,
        "annual_spending": annual_spending,
        "salary_growth_rate": salary_growth_rate,
        "inflation_rate": inflation_rate,
        "investment_return_rate": investment_return_rate,
        "retirement_year": retirement_year,
        "retirement_spending_adj": retirement_spending_adj,
        "horizon_year": horizon_year,
    })
    return RedirectResponse("/wealth", status_code=303)
