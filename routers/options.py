import os
import uuid
from typing import Optional

from fastapi import APIRouter, Request, Form, UploadFile, File
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

import db.factory as fdb
import auth
from config import CURRENCIES, QTY_TYPES, OPTION_SCOPES, IMAGES_DIR

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
    return templates.TemplateResponse(request, "options.html", {
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
                      conflict_group: str = Form(""),
                      image_priority: int = Form(0),
                      current_image_path: str = Form(""),
                      image: Optional[UploadFile] = File(None)):
    auth.require_user(request)

    image_path = current_image_path
    if image and image.filename:
        os.makedirs(IMAGES_DIR, exist_ok=True)
        ext = image.filename.rsplit(".", 1)[-1].lower()
        fname = f"opt_{uuid.uuid4().hex[:10]}.{ext}"
        fpath = os.path.join(IMAGES_DIR, fname)
        content = await image.read()
        with open(fpath, "wb") as f:
            f.write(content)
        image_path = f"img/uploads/{fname}"

    kw = dict(
        name=name, description=description, price=price, currency=currency,
        scope=scope, category_id=category_id or None, qty_type=qty_type,
        conflict_group=conflict_group, image_priority=image_priority,
        image_path=image_path,
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
