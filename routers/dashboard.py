from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
import db.factory as fdb
import auth

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/")
async def dashboard(request: Request):
    user = auth.require_user(request)
    stats = fdb.get_stats()
    recent_offers = fdb.get_recent_offers(10)
    customers = {c["id"]: c for c in fdb.get_customers()}
    models = {m["id"]: m for m in fdb.get_models()}
    for o in recent_offers:
        o["customer_name"] = customers.get(o.get("customer_id"), {}).get("name", "-")
        o["model_name"] = models.get(o.get("model_id"), {}).get("name", "-")
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user": user,
        "stats": stats,
        "recent_offers": recent_offers,
        "active_page": "dashboard",
    })
