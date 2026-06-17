import os
import uuid
import io
import zipfile
import datetime
from typing import Optional

from fastapi import APIRouter, Request, Form, UploadFile, File
from fastapi.responses import RedirectResponse, StreamingResponse

import db.users as udb
import db.factory as fdb
import auth
from config import IMAGES_DIR, BASE_DIR, DATA_DIR

router = APIRouter(prefix="/admin")
from tmpl import templates


@router.get("")
async def admin_page(request: Request):
    user = auth.require_admin(request)
    users = udb.all_users()
    company = fdb.get_company()
    categories = fdb.get_cats()
    manufacturers = udb.all_manufacturers()
    models = fdb.get_models()
    return templates.TemplateResponse(request, "admin.html", {
        "user": user,
        "users": users,
        "company": company,
        "categories": categories,
        "manufacturers": manufacturers,
        "models": models,
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


@router.post("/update-user")
async def update_user(request: Request,
                      uid: int = Form(...),
                      role: str = Form("dealer"),
                      is_approved: int = Form(0),
                      is_active: int = Form(0),
                      can_view_costs: int = Form(0),
                      parent_id: int = Form(0)):
    auth.require_admin(request)
    form = await request.form()
    allowed_menus = ",".join(form.getlist("allowed_menus"))
    allowed_categories = ",".join(form.getlist("allowed_categories"))
    allowed_actions = ",".join(form.getlist("allowed_actions"))
    udb.update_admin(uid,
        role=role,
        is_approved=is_approved,
        is_active=is_active,
        can_view_costs=can_view_costs,
        allowed_menus=allowed_menus,
        allowed_categories=allowed_categories,
        parent_id=parent_id if parent_id else None,
        allowed_actions=allowed_actions,
    )
    return RedirectResponse("/admin?tab=users", 303)


@router.post("/impersonate/exit")
async def exit_impersonation(request: Request):
    admin_token = request.cookies.get("admin_session")
    if not admin_token:
        return RedirectResponse("/", 303)
    resp = RedirectResponse("/admin?tab=users", 303)
    resp.set_cookie("session", admin_token, max_age=86400 * 30, httponly=True, samesite="lax")
    resp.delete_cookie("admin_session")
    return resp


@router.post("/impersonate/{uid}")
async def impersonate_user(request: Request, uid: int):
    auth.require_admin(request)
    target = udb.by_id(uid)
    if not target or target["role"] == "admin":
        return RedirectResponse("/admin?tab=users", 303)
    current_token = request.cookies.get("session")
    resp = RedirectResponse("/", 303)
    resp.set_cookie("admin_session", current_token, max_age=3600, httponly=True, samesite="lax")
    resp.set_cookie("session", auth.make_session(uid), max_age=3600, httponly=True, samesite="lax")
    return resp


@router.get("/backup/download")
async def backup_download(request: Request):
    auth.require_admin(request)
    buf = io.BytesIO()
    now = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # DB files
        for fname in os.listdir(DATA_DIR):
            fpath = os.path.join(DATA_DIR, fname)
            if os.path.isfile(fpath):
                zf.write(fpath, f"data/{fname}")
        # Uploaded images
        if os.path.isdir(IMAGES_DIR):
            for fname in os.listdir(IMAGES_DIR):
                fpath = os.path.join(IMAGES_DIR, fname)
                if os.path.isfile(fpath):
                    zf.write(fpath, f"static/img/uploads/{fname}")
    buf.seek(0)
    filename = f"teklif_yedek_{now}.zip"
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/delivery-terms")
async def delivery_terms_page(request: Request):
    user = auth.require_admin(request)
    terms = fdb.get_delivery_terms()
    return templates.TemplateResponse(request, "delivery_terms.html", {
        "user": user,
        "terms": terms,
        "active_page": "admin",
        "msg": request.query_params.get("msg", ""),
        "msg_type": request.query_params.get("msg_type", "info"),
    })


@router.post("/delivery-terms/save")
async def save_delivery_term(request: Request,
                              id: int = Form(0),
                              name: str = Form(...),
                              discount_pct: float = Form(0.0),
                              sort_order: int = Form(0),
                              is_active: int = Form(1)):
    auth.require_admin(request)
    if id:
        fdb.upd_delivery_term(id, name, discount_pct, sort_order, is_active)
    else:
        fdb.add_delivery_term(name, discount_pct, sort_order)
    return RedirectResponse("/admin/delivery-terms?msg=Kaydedildi&msg_type=success", 303)


@router.post("/delivery-terms/delete")
async def delete_delivery_term(request: Request, id: int = Form(...)):
    auth.require_admin(request)
    fdb.del_delivery_term(id)
    return RedirectResponse("/admin/delivery-terms?msg=Silindi&msg_type=success", 303)


@router.post("/smtp")
async def save_smtp(request: Request,
                    smtp_host: str = Form(""),
                    smtp_port: int = Form(587),
                    smtp_user: str = Form(""),
                    smtp_pass: str = Form(""),
                    smtp_from: str = Form("")):
    auth.require_admin(request)
    fdb.save_company(smtp_host=smtp_host, smtp_port=smtp_port,
                     smtp_user=smtp_user, smtp_pass=smtp_pass, smtp_from=smtp_from)
    return RedirectResponse("/admin?tab=system&msg=SMTP+ayarları+kaydedildi&msg_type=success", 303)


@router.post("/backup/restore")
async def backup_restore(request: Request, backup_file: UploadFile = File(...)):
    auth.require_admin(request)
    content = await backup_file.read()
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            names = zf.namelist()
            # Validate: must contain data/ files
            if not any(n.startswith("data/") for n in names):
                return RedirectResponse("/admin?tab=system&msg=Geçersiz+yedek+dosyası&msg_type=error", 303)
            for name in names:
                if name.startswith("data/"):
                    fname = os.path.basename(name)
                    if fname:
                        dest = os.path.join(DATA_DIR, fname)
                        with zf.open(name) as src, open(dest, "wb") as dst:
                            dst.write(src.read())
                elif name.startswith("static/img/uploads/"):
                    fname = os.path.basename(name)
                    if fname:
                        os.makedirs(IMAGES_DIR, exist_ok=True)
                        dest = os.path.join(IMAGES_DIR, fname)
                        with zf.open(name) as src, open(dest, "wb") as dst:
                            dst.write(src.read())
    except Exception as e:
        return RedirectResponse(f"/admin?tab=system&msg=Yedek+yüklenemedi:+{e}&msg_type=error", 303)
    return RedirectResponse("/admin?tab=system&msg=Yedek+başarıyla+yüklendi.+Sunucuyu+yeniden+başlatın.&msg_type=success", 303)
