import secrets

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse

from app.auth import (
    CSRF_COOKIE_NAME,
    _CSRF_COOKIE_KWARGS,
    get_current_user,
    require_admin,
    verify_csrf,
)
from app.services import gallery as gallery_svc
from app.models.gallery import all_categories, init_db
from app.templates_config import templates

init_db()

router = APIRouter()

CATEGORIES = gallery_svc.CATEGORIES


@router.get("/gallery", response_class=HTMLResponse)
async def gallery_index(request: Request):
    user = get_current_user(request)
    cat_filter = request.query_params.get("category")
    if cat_filter and cat_filter in CATEGORIES:
        images = gallery_svc.get_images_by_category(cat_filter)
    else:
        images = gallery_svc.get_all_images()
        cat_filter = None
    token = secrets.token_hex(16)
    resp = templates.TemplateResponse("gallery/index.html", {
        "request": request,
        "user": user,
        "active": "gallery",
        "images": images,
        "categories": CATEGORIES,
        "cat_filter": cat_filter,
        "csrf_token": token,
    })
    resp.set_cookie(CSRF_COOKIE_NAME, token, **_CSRF_COOKIE_KWARGS)
    return resp


@router.get("/gallery/upload", response_class=HTMLResponse)
async def gallery_upload_get(request: Request, user=Depends(require_admin)):
    token = secrets.token_hex(16)
    resp = templates.TemplateResponse("gallery/upload.html", {
        "request": request,
        "user": user,
        "active": "gallery_upload",
        "categories": CATEGORIES,
        "csrf_token": token,
        "errors": {},
    })
    resp.set_cookie(CSRF_COOKIE_NAME, token, **_CSRF_COOKIE_KWARGS)
    return resp


@router.post("/gallery/upload")
async def gallery_upload_post(
    request: Request,
    user=Depends(require_admin),
    _csrf: None = Depends(verify_csrf),
    category: str = Form(...),
    title: str = Form(""),
    csrf_token: str = Form(...),
    file: UploadFile = File(...),
):
    errors: dict = {}
    if category not in CATEGORIES:
        errors["category"] = "Select a valid category."
    if not file.filename:
        errors["file"] = "A file is required."

    if not errors:
        try:
            data = await file.read()
            gallery_svc.save_image(data, file.filename, category, title)
        except ValueError as exc:
            errors["file"] = str(exc)

    if errors:
        new_csrf = secrets.token_hex(16)
        resp = templates.TemplateResponse("gallery/upload.html", {
            "request": request,
            "user": user,
            "active": "gallery_upload",
            "categories": CATEGORIES,
            "csrf_token": new_csrf,
            "errors": errors,
            "values": {"category": category, "title": title},
        }, status_code=422)
        resp.set_cookie(CSRF_COOKIE_NAME, new_csrf, **_CSRF_COOKIE_KWARGS)
        return resp

    return RedirectResponse("/gallery", status_code=303)


@router.post("/gallery/{image_id}/rotate")
async def gallery_rotate(
    image_id: int,
    request: Request,
    user=Depends(require_admin),
    _csrf: None = Depends(verify_csrf),
    csrf_token: str = Form(...),
    direction: str = Form("cw"),
):
    if direction not in ("cw", "ccw"):
        return HTMLResponse("Invalid direction.", status_code=400)
    gallery_svc.rotate_image(image_id, direction)
    return RedirectResponse("/gallery", status_code=303)


@router.post("/gallery/{image_id}/delete")
async def gallery_delete(
    image_id: int,
    request: Request,
    user=Depends(require_admin),
    _csrf: None = Depends(verify_csrf),
    csrf_token: str = Form(...),
):
    gallery_svc.remove_image(image_id)
    return RedirectResponse("/gallery", status_code=303)
