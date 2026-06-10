import os
import uuid
from typing import Optional

from fastapi import APIRouter, Request, Form, UploadFile, File
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

import db.users as udb
import auth
from config import IMAGES_DIR, LANGS

router = APIRouter(prefix="/profile")
templates = Jinja2Templates(directory="templates")


@router.get("")
async def profile_page(request: Request):
    user = auth.require_user(request)
    return templates.TemplateResponse("profile.html", {
        "request": request,
        "user": user,
        "langs": LANGS,
        "active_page": "profile",
    })


@router.post("/save")
async def save_profile(request: Request,
                       company_name: str = Form(""),
                       phone: str = Form(""),
                       website: str = Form(""),
                       address: str = Form(""),
                       logo: Optional[UploadFile] = File(None)):
    user = auth.require_user(request)
    logo_path = ""
    if logo and logo.filename:
        os.makedirs(IMAGES_DIR, exist_ok=True)
        ext = os.path.splitext(logo.filename)[1].lower() or ".png"
        fname = f"logo_{user['id']}_{uuid.uuid4().hex[:8]}{ext}"
        fpath = os.path.join(IMAGES_DIR, fname)
        content = await logo.read()
        try:
            from PIL import Image as PILImage
            import io as _io
            img = PILImage.open(_io.BytesIO(content))
            img.thumbnail((400, 400))
            img.save(fpath, "PNG")
        except Exception:
            with open(fpath, "wb") as f:
                f.write(content)
        logo_path = f"img/uploads/{fname}"
    kw = dict(company_name=company_name, phone=phone, website=website, address=address)
    if logo_path:
        kw["logo_path"] = logo_path
    udb.update_profile(user["id"], **kw)
    return RedirectResponse("/profile", 303)


@router.post("/password")
async def change_password(request: Request,
                          current_password: str = Form(...),
                          new_password: str = Form(...),
                          confirm_password: str = Form(...)):
    user = auth.require_user(request)
    u = udb.by_id(user["id"])
    if not udb.check_pw(current_password, u["password"]):
        return templates.TemplateResponse("profile.html", {
            "request": request,
            "user": user,
            "msg": "Mevcut şifre hatalı.",
            "msg_type": "danger",
            "langs": LANGS,
            "active_page": "profile",
        })
    if new_password != confirm_password:
        return templates.TemplateResponse("profile.html", {
            "request": request,
            "user": user,
            "msg": "Yeni şifreler eşleşmiyor.",
            "msg_type": "danger",
            "langs": LANGS,
            "active_page": "profile",
        })
    udb.change_pw(user["id"], new_password)
    return templates.TemplateResponse("profile.html", {
        "request": request,
        "user": user,
        "msg": "Şifreniz başarıyla güncellendi.",
        "msg_type": "success",
        "langs": LANGS,
        "active_page": "profile",
    })


@router.post("/preferences")
async def save_prefs(request: Request,
                     lang: str = Form("tr"),
                     theme: str = Form("dark")):
    user = auth.require_user(request)
    udb.update_profile(user["id"], lang=lang, theme=theme)
    return RedirectResponse("/profile", 303)
