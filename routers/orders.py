from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
import db.factory as fdb
import auth

router = APIRouter(prefix="/orders")
templates = Jinja2Templates(directory="templates")


@router.get("")
async def orders_list(request: Request):
    user = auth.require_user(request)
    orders = fdb.get_offers(status="Sipariş Verildi")
    customers = {c["id"]: c for c in fdb.get_customers()}
    models = {m["id"]: m for m in fdb.get_models()}
    for o in orders:
        o["customer_name"] = customers.get(o.get("customer_id"), {}).get("name", "-")
        o["model_name"] = models.get(o.get("model_id"), {}).get("name", "-")
    return templates.TemplateResponse(request, "orders.html", {
        "user": user,
        "orders": orders,
        "active_page": "orders",
    })
