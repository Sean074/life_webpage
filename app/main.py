from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles

from app.auth import get_current_user
from app.routes.auth_routes import router as auth_router
from app.routes.blog import router as blog_router
from app.routes.gallery import router as gallery_router
from app.routes.library import router as library_router
from app.routes.wealth import router as wealth_router
from app.services.blog import get_recent_posts
from app.templates_config import templates

app = FastAPI()
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.mount("/art", StaticFiles(directory="data/images"), name="art")
app.include_router(auth_router)
app.include_router(blog_router)
app.include_router(gallery_router)
app.include_router(library_router)
app.include_router(wealth_router)


@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse("index.html", {
        "request": request,
        "user": get_current_user(request),
        "active": "home",
        "recent_posts": get_recent_posts(3),
        "show_margin_gallery": True,
    })
