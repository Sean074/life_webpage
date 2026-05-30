from dotenv import load_dotenv
load_dotenv()

import sqlite3
from fastapi import FastAPI, Request
from fastapi.exception_handlers import http_exception_handler as default_http_exception_handler
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.auth import get_current_user
from app.routes.admin import router as admin_router
from app.routes.auth_routes import router as auth_router
from app.routes.blog import router as blog_router
from app.routes.gallery import router as gallery_router
from app.routes.library import router as library_router
from app.routes.expenses import router as expenses_router
from app.routes.wealth import router as wealth_router
from app.routes.health import router as health_router
from app.services.blog import get_recent_posts
from app.templates_config import templates

app = FastAPI()
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.mount("/art", StaticFiles(directory="data/images"), name="art")
app.include_router(admin_router)
app.include_router(auth_router)
app.include_router(blog_router)
app.include_router(gallery_router)
app.include_router(library_router)
app.include_router(expenses_router)
app.include_router(wealth_router)
app.include_router(health_router)


@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        user = get_current_user(request)
        return templates.TemplateResponse("404.html", {"request": request, "user": user}, status_code=404)
    if exc.status_code >= 500:
        user = get_current_user(request)
        return templates.TemplateResponse("500.html", {"request": request, "user": user}, status_code=exc.status_code)
    return await default_http_exception_handler(request, exc)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    try:
        user = get_current_user(request)
    except Exception:
        user = None
    return templates.TemplateResponse("500.html", {"request": request, "user": user}, status_code=500)


@app.get("/healthz")
async def healthz():
    try:
        conn = sqlite3.connect("file:data/library.db?mode=ro", uri=True)
        conn.execute("SELECT 1")
        conn.close()
        return {"ok": True}
    except Exception:
        return JSONResponse({"ok": False}, status_code=500)


@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse("index.html", {
        "request": request,
        "user": get_current_user(request),
        "active": "home",
        "recent_posts": get_recent_posts(3),
        "show_margin_gallery": True,
    })
