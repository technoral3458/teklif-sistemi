from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
import db.factory as fdb
import auth

router = APIRouter(prefix="/costs")
templates = Jinja2Templates(directory="templates")


@router.get("")
async def costs_page(request: Request, model_id: int = 0):
    user = auth.require_user(request)
    models = fdb.get_models()

    if model_id:
        selected = fdb.get_model(model_id)
        models_to_show = [selected] if selected else models
    else:
        models_to_show = models

    cost_data = []
    for m in models_to_show:
        purchase = float(m.get("purchase_price") or 0)
        shipping = float(m.get("shipping_cost") or 0)
        customs_pct = float(m.get("customs_pct") or 0)
        extra_pct = float(m.get("extra_tax_pct") or 0)
        port = float(m.get("port_cost") or 0)
        doc = float(m.get("document_cost") or 0)
        inst = float(m.get("installation_cost") or 0)
        other = float(m.get("other_cost") or 0)
        customs = purchase * customs_pct / 100
        extra = purchase * extra_pct / 100
        total_cost = purchase + shipping + customs + extra + port + doc + inst + other
        sale_price = float(m.get("base_price") or 0)
        profit = sale_price - total_cost
        margin = (profit / sale_price * 100) if sale_price else 0
        cost_data.append({
            "model": m,
            "purchase": purchase,
            "shipping": shipping,
            "customs": customs,
            "extra": extra,
            "port": port,
            "doc": doc,
            "inst": inst,
            "other": other,
            "total_cost": total_cost,
            "sale_price": sale_price,
            "profit": profit,
            "margin": margin,
        })

    return templates.TemplateResponse(request, "costs.html", {
        "user": user,
        "models": models,
        "cost_data": cost_data,
        "selected_model_id": model_id,
        "active_page": "costs",
    })
