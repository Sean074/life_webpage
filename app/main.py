from dotenv import load_dotenv
load_dotenv()

import sqlite3
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.exception_handlers import http_exception_handler as default_http_exception_handler
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.auth import DB_PATH, check_secret_key, get_current_user
from app.models import expenses as expenses_model
from app.models import health as health_model
from app.models import wealth as wealth_model
from app.services import wealth as wealth_svc
from app.routes.admin import router as admin_router
from app.routes.auth_routes import router as auth_router
from app.routes.blog import router as blog_router
from app.routes.gallery import router as gallery_router
from app.routes.expenses import router as expenses_router
from app.routes.wealth import router as wealth_router
from app.routes.health import router as health_router
from app.routes.today import router as today_router
from app.routes.projects import router as projects_router
from app.services.blog import get_recent_posts
from app.templates_config import templates


# Resolve from this file, not the CWD, so the app serves the same files however it is started.
_ROOT = Path(__file__).resolve().parent.parent
_IMAGES_DIR = _ROOT / "data" / "images"


@asynccontextmanager
async def lifespan(app: FastAPI):
    check_secret_key()
    _IMAGES_DIR.mkdir(parents=True, exist_ok=True)  # gitignored; absent on a fresh install
    expenses_model.init_db()
    health_model.init_db()
    wealth_model.init_db(seed_accounts=wealth_svc.latest_accounts_from_csv())
    yield


app = FastAPI(lifespan=lifespan)


app.mount("/static", StaticFiles(directory=_ROOT / "app" / "static"), name="static")
# check_dir=False: the directory is created in lifespan(), which runs after this module is imported.
app.mount("/art", StaticFiles(directory=_IMAGES_DIR, check_dir=False), name="art")
app.include_router(admin_router)
app.include_router(auth_router)
app.include_router(blog_router)
app.include_router(gallery_router)
app.include_router(expenses_router)
app.include_router(wealth_router)
app.include_router(health_router)
app.include_router(today_router)
app.include_router(projects_router)


@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        user = get_current_user(request)
        return templates.TemplateResponse(request, "404.html", {"user": user}, status_code=404)
    if exc.status_code >= 500:
        user = get_current_user(request)
        return templates.TemplateResponse(request, "500.html", {"user": user}, status_code=exc.status_code)
    return await default_http_exception_handler(request, exc)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    try:
        user = get_current_user(request)
    except Exception:
        user = None
    return templates.TemplateResponse(request, "500.html", {"user": user}, status_code=500)


@app.get("/healthz")
async def healthz():
    try:
        conn = sqlite3.connect(f"{Path(DB_PATH).resolve().as_uri()}?mode=ro", uri=True)
        conn.execute("SELECT 1")
        conn.close()
        return {"ok": True}
    except Exception:
        return JSONResponse({"ok": False}, status_code=500)


@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse(request, "index.html", {
        "user": get_current_user(request),
        "active": "home",
        "recent_posts": get_recent_posts(3),
        "show_margin_gallery": True,
    })
