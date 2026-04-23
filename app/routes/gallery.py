import secrets

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse

from app.auth import get_current_user, require_admin
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
    response = templates.TemplateResponse("gallery/index.html", {
        "request": request,
        "user": user,
        "active": "gallery",
        "images": images,
        "categories": CATEGORIES,
        "cat_filter": cat_filter,
    })
    if user and user.get("role") == "admin":
        csrf_token = secrets.token_hex(16)
        response.set_cookie("csrf_token", csrf_token, httponly=False, samesite="lax")
    return response


@router.get("/gallery/upload", response_class=HTMLResponse)
async def gallery_upload_get(request: Request, user=Depends(require_admin)):
    csrf_token = secrets.token_hex(16)
    response = templates.TemplateResponse("gallery/upload.html", {
        "request": request,
        "user": user,
        "active": "gallery_upload",
        "categories": CATEGORIES,
        "csrf_token": csrf_token,
        "errors": {},
    })
    response.set_cookie("csrf_token", csrf_token, httponly=False, samesite="lax")
    return response


@router.post("/gallery/upload")
async def gallery_upload_post(
    request: Request,
    user=Depends(require_admin),
    category: str = Form(...),
    title: str = Form(""),
    csrf_token: str = Form(...),
    file: UploadFile = File(...),
):
    cookie_csrf = request.cookies.get("csrf_token", "")
    if not secrets.compare_digest(csrf_token, cookie_csrf):
        return templates.TemplateResponse("gallery/upload.html", {
            "request": request,
            "user": user,
            "active": "gallery",
            "categories": CATEGORIES,
            "csrf_token": csrf_token,
            "errors": {"csrf": "Invalid request. Please try again."},
        }, status_code=400)

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
        resp.set_cookie("csrf_token", new_csrf, httponly=False, samesite="lax")
        return resp

    return RedirectResponse("/gallery", status_code=303)


@router.post("/gallery/{image_id}/rotate")
async def gallery_rotate(image_id: int, request: Request, user=Depends(require_admin)):
    form = await request.form()
    csrf_token = form.get("csrf_token", "")
    cookie_csrf = request.cookies.get("csrf_token", "")
    if not secrets.compare_digest(csrf_token, cookie_csrf):
        return HTMLResponse("Invalid request.", status_code=400)
    direction = form.get("direction", "cw")
    if direction not in ("cw", "ccw"):
        return HTMLResponse("Invalid direction.", status_code=400)
    gallery_svc.rotate_image(image_id, direction)
    return RedirectResponse("/gallery", status_code=303)


@router.post("/gallery/{image_id}/delete")
async def gallery_delete(image_id: int, request: Request, user=Depends(require_admin)):
    form = await request.form()
    csrf_token = form.get("csrf_token", "")
    cookie_csrf = request.cookies.get("csrf_token", "")
    if not secrets.compare_digest(csrf_token, cookie_csrf):
        return HTMLResponse("Invalid request.", status_code=400)
    gallery_svc.remove_image(image_id)
    return RedirectResponse("/gallery", status_code=303)
