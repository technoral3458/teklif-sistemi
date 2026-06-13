from fastapi import APIRouter, Request
import db.factory as fdb
import db.users as udb
import auth

router = APIRouter()
from tmpl import templates


@router.get("/")
async def dashboard(request: Request):
    user = auth.require_user(request)
    role = user["role"]

    if role == "manufacturer":
        mfr_id = udb.effective_mfr_id(user)
        stats = fdb.get_stats(manufacturer_id=mfr_id)
        recent_offers = fdb.get_recent_offers(10, manufacturer_id=mfr_id)
    elif role == "dealer":
        stats = fdb.get_stats(dealer_id=user["id"])
        recent_offers = fdb.get_recent_offers(10, dealer_id=user["id"])
    else:
        stats = fdb.get_stats()
        recent_offers = fdb.get_recent_offers(10)

    customers = {c["id"]: c for c in fdb.get_customers()}
    models = {m["id"]: m for m in fdb.get_models()}
    for o in recent_offers:
        o["customer_name"] = customers.get(o.get("customer_id"), {}).get("name", "-")
        o["model_name"] = models.get(o.get("model_id"), {}).get("name", "-")
    return templates.TemplateResponse(request, "dashboard.html", {
        "user": user,
        "stats": stats,
        "recent_offers": recent_offers,
        "active_page": "dashboard",
    })
