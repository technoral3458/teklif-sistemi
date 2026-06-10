from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
import db.factory as fdb
import auth
from config import CURRENCIES, QTY_TYPES, OPTION_SCOPES

router = APIRouter(prefix="/options")
templates = Jinja2Templates(directory="templates")


@router.get("")
async def options_list(request: Request):
    user = auth.require_user(request)
    options = fdb.get_options()
    cats = fdb.get_cats()
    cat_map = {c["id"]: c["name"] for c in cats}
    for o in options:
        o["category_name"] = cat_map.get(o.get("category_id"), "Genel")
    return templates.TemplateResponse("options.html", {
        "request": request,
        "user": user,
        "options": options,
        "categories": cats,
        "currencies": CURRENCIES,
        "qty_types": QTY_TYPES,
        "option_scopes": OPTION_SCOPES,
        "active_page": "options",
    })


@router.post("/save")
async def save_option(request: Request,
                      id: int = Form(0),
                      name: str = Form(...),
                      description: str = Form(""),
                      price: float = Form(0.0),
                      currency: str = Form("USD"),
                      scope: str = Form("GLOBAL"),
                      category_id: int = Form(0),
                      qty_type: str = Form("MANUAL"),
                      conflict_group: str = Form("")):
    auth.require_user(request)
    kw = dict(
        name=name, description=description, price=price, currency=currency,
        scope=scope, category_id=category_id or None, qty_type=qty_type,
        conflict_group=conflict_group,
    )
    if id:
        fdb.upd_option(id, **kw)
    else:
        fdb.add_option(**kw)
    return RedirectResponse("/options", 303)


@router.post("/delete")
async def delete_option(request: Request, id: int = Form(...)):
    auth.require_user(request)
    fdb.del_option(id)
    return RedirectResponse("/options", 303)
