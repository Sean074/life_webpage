from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, Response

from app.auth import get_current_user
from app.services import atmos_tool
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
    {
        "slug": "atmos",
        "name": "ATMOS",
        "tagline": "Standard atmosphere lookups, airspeed conversions and speed-altitude charts — run it in the browser",
    },
    {
        "slug": "russian-atelier-year",
        "name": "Russian Atelier Year",
        "tagline": "A 12-month drawing and painting plan in the Russian academic tradition — Chistyakov, Repin, Serov, Sargent",
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


# ATMOS web tool — public and GET-only (calculations change no state, so no
# CSRF surface). Sync handlers so the engine runs in the threadpool, not on
# the event loop. Must be registered before /projects/{slug}.
@router.get("/projects/atmos", response_class=HTMLResponse)
def atmos_page(request: Request):
    q = request.query_params
    calc = q.get("calc")
    props = speed = None
    if calc == "props":
        props = atmos_tool.atmos_props(q.get("model", ""), q.get("mode", ""), q.get("value"), q.get("unit", ""))
    elif calc == "speed":
        speed = atmos_tool.speed_convert(
            q.get("model", ""), q.get("alt"), q.get("alt_unit", ""),
            q.get("speed_type", ""), q.get("value"), q.get("unit", ""),
        )
    chart = {
        "model": q.get("model", atmos_tool.DEFAULT_MODEL),
        "x": q.get("x", "kcas"),
        "envelope": q.get("envelope", "speed_envelope_example.json"),
    }
    if calc != "chart" or not atmos_tool.chart_params_valid(chart["model"], chart["x"], chart["envelope"]):
        chart = {"model": atmos_tool.DEFAULT_MODEL, "x": "kcas", "envelope": "speed_envelope_example.json"}
    return templates.TemplateResponse(request, "projects/atmos.html", {
        "user": get_current_user(request),
        "active": "projects",
        "project": _get_project("atmos"),
        "calc": calc,
        "q": q,
        "props": props,
        "speed": speed,
        "chart": chart,
        "tool": atmos_tool,
    })


@router.get("/projects/atmos/chart.svg")
def atmos_chart(model: str = "", x: str = "", envelope: str = ""):
    if not atmos_tool.chart_params_valid(model, x, envelope):
        raise HTTPException(status_code=400)
    return Response(
        atmos_tool.chart_svg(model, x, envelope),
        media_type="image/svg+xml",
        headers={
            "Cache-Control": "public, max-age=86400",
            "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'",
        },
    )


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
