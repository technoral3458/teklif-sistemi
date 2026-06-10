import os
import uuid
from typing import Optional

from fastapi import APIRouter, Request, Form, UploadFile, File
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

import db.users as udb
import db.factory as fdb
import auth
from config import IMAGES_DIR

router = APIRouter(prefix="/admin")
templates = Jinja2Templates(directory="templates")


@router.get("")
async def admin_page(request: Request):
    user = auth.require_admin(request)
    users = udb.all_users()
    company = fdb.get_company()
    return templates.TemplateResponse(request, "admin.html", {
        "user": user,
        "users": users,
        "company": company,
        "active_page": "admin",
    })


@router.post("/company")
async def save_company(request: Request,
                       company_name: str = Form(""),
                       address: str = Form(""),
                       phone: str = Form(""),
                       website: str = Form(""),
                       tax_id: str = Form(""),
                       email: str = Form(""),
                       logo: Optional[UploadFile] = File(None)):
    auth.require_admin(request)
    logo_path = ""
    if logo and logo.filename:
        os.makedirs(IMAGES_DIR, exist_ok=True)
        fname = f"company_logo_{uuid.uuid4().hex[:8]}.png"
        fpath = os.path.join(IMAGES_DIR, fname)
        content = await logo.read()
        with open(fpath, "wb") as f:
            f.write(content)
        logo_path = f"img/uploads/{fname}"
    kw = dict(
        company_name=company_name, address=address,
        phone=phone, website=website, tax_id=tax_id, email=email,
    )
    if logo_path:
        kw["logo_path"] = logo_path
    fdb.save_company(**kw)
    return RedirectResponse("/admin", 303)
