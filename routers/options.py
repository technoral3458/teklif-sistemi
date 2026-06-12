import os
import uuid
from typing import Optional, List

from fastapi import APIRouter, Request, Form, UploadFile, File
from fastapi.responses import RedirectResponse

import db.factory as fdb
import auth
from config import CURRENCIES, QTY_TYPES, OPTION_SCOPES, IMAGES_DIR

router = APIRouter(prefix="/options")
from tmpl import templates


@router.get("")
async def options_list(request: Request):
    user = auth.require_user(request)
    options = fdb.get_options()
    cats = fdb.get_cats()
    cat_map = {c["id"]: c["name"] for c in cats}
    for o in options:
        cids = [int(x) for x in (o.get("category_ids") or "").split(",") if x.strip().isdigit()]
        o["category_names"] = ", ".join(cat_map[c] for c in cids if c in cat_map) or "Genel"
    return templates.TemplateResponse(request, "options.html", {
        "user": user,
        "options": options,
        "categories": cats,
        "currencies": CURRENCIES,
        "qty_types": QTY_TYPES,
        "option_scopes": OPTION_SCOPES,
        "active_page": "options",
        "msg": request.query_params.get("msg", ""),
        "msg_type": request.query_params.get("msg_type", "info"),
    })


@router.post("/save")
async def save_option(request: Request,
                      id: int = Form(0),
                      name: str = Form(...),
                      description: str = Form(""),
                      price: float = Form(0.0),
                      currency: str = Form("USD"),
                      scope: str = Form("GLOBAL"),
                      category_ids: List[int] = Form([]),
                      qty_type: str = Form("MANUAL"),
                      conflict_group: str = Form(""),
                      image_priority: int = Form(0),
                      current_image_path: str = Form(""),
                      current_variation_image_path: str = Form(""),
                      image: Optional[UploadFile] = File(None),
                      variation_image: Optional[UploadFile] = File(None),
                      name_en: str = Form(""),
                      description_en: str = Form(""),
                      name_zh: str = Form(""),
                      description_zh: str = Form(""),
                      video_url: str = Form("")):
    auth.require_user(request)

    def _save_file(upload: UploadFile, prefix: str) -> str:
        raise NotImplementedError

    async def _save(upload, prefix):
        if not (upload and upload.filename):
            return None
        os.makedirs(IMAGES_DIR, exist_ok=True)
        ext = os.path.splitext(upload.filename)[1].lower() or ".jpg"
        fname = f"{prefix}_{uuid.uuid4().hex[:10]}{ext}"
        content = await upload.read()
        with open(os.path.join(IMAGES_DIR, fname), "wb") as f:
            f.write(content)
        return f"img/uploads/{fname}"

    try:
        image_path = (await _save(image, "opt")) or current_image_path
        variation_image_path = (await _save(variation_image, "var")) or current_variation_image_path
    except Exception as e:
        return RedirectResponse(f"/options?msg=Resim+kaydedilemedi:+{e}&msg_type=error", 303)

    kw = dict(
        name=name, description=description, price=price, currency=currency,
        scope=scope, category_ids=",".join(str(c) for c in category_ids), qty_type=qty_type,
        conflict_group=conflict_group, image_priority=image_priority,
        image_path=image_path, variation_image_path=variation_image_path,
        video_url=video_url.strip(),
        name_en=name_en, description_en=description_en,
        name_zh=name_zh, description_zh=description_zh,
    )
    try:
        if id:
            fdb.upd_option(id, **kw)
        else:
            fdb.add_option(**kw)
    except Exception as e:
        return RedirectResponse(f"/options?msg=Kayıt+hatası:+{e}&msg_type=error", 303)
    return RedirectResponse("/options?msg=Kaydedildi&msg_type=success", 303)


@router.post("/delete")
async def delete_option(request: Request, id: int = Form(...)):
    auth.require_user(request)
    fdb.del_option(id)
    return RedirectResponse("/options", 303)
