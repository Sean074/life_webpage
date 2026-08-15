from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse

from app.auth import get_current_user
from app.templates_config import templates

router = APIRouter()

# Registry of project brochure pages. Adding an entry here (plus a matching
# templates/projects/<slug>.html and figures under static/img/projects/<slug>/)
# publishes a new page — e.g. smodal, sbeam.
PROJECTS = [
    {
        "slug": "sloads",
        "name": "sloads",
        "tagline": "FAR 23 structural design loads — suite replication grown into a concept distributed-loads tool",
    },
]


def _get_project(slug: str):
    for p in PROJECTS:
        if p["slug"] == slug:
            return p
    return None


@router.get("/projects", response_class=HTMLResponse)
async def projects_index(request: Request):
    return templates.TemplateResponse(request, "projects/index.html", {
        "user": get_current_user(request),
        "active": "projects",
        "projects": PROJECTS,
    })


@router.get("/projects/{slug}", response_class=HTMLResponse)
async def project_page(request: Request, slug: str):
    project = _get_project(slug)
    if project is None:
        raise HTTPException(status_code=404)
    return templates.TemplateResponse(request, f"projects/{slug}.html", {
        "user": get_current_user(request),
        "active": "projects",
        "project": project,
    })
