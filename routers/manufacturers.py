from urllib.parse import urlencode

from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
import db.users as udb
import db.factory as fdb
import auth
import security

router = APIRouter(prefix="/manufacturers")
from tmpl import templates

SPAM_THRESHOLD = 3


@router.get("")
async def manufacturers_list(request: Request):
    user = auth.require_admin(request)
    all_users = udb.all_users()
    manufacturers = [u for u in all_users if u["role"] == "manufacturer" or u.get("is_manufacturer")]

    # Kayıt ekranından "Üretici" seçen botlar bu listeye düşer
    ip_counts = udb.reg_ip_counts()
    for m in manufacturers:
        m["spam_score"], m["spam_reasons"] = security.spam_score(m, ip_counts)
    suspicious = sorted(
        (m for m in manufacturers if m["spam_score"] >= SPAM_THRESHOLD),
        key=lambda m: -m["spam_score"],
    )

    cats = fdb.get_cats()
    models = fdb.get_models()
    return templates.TemplateResponse(request, "manufacturers.html", {
        "user": user,
        "manufacturers": manufacturers,
        "suspicious": suspicious,
        "categories": cats,
        "models": models,
        "active_page": "manufacturers",
        "msg": request.query_params.get("msg"),
        "msg_type": request.query_params.get("msg_type", "info"),
    })


@router.post("/bulk")
async def bulk_manufacturers(request: Request):
    """Seçili üretici hesaplarını topluca sil / onayla / pasife al."""
    acting = auth.require_admin(request)
    form = await request.form()
    ids = form.getlist("ids")
    action = (form.get("action") or "").strip()

    if not ids:
        return RedirectResponse(
            "/manufacturers?" + urlencode({"msg": "Hiç kayıt seçilmedi.", "msg_type": "warning"}), 303)

    if action == "delete":
        n = udb.bulk_delete(ids, protect_id=acting["id"])
        msg = f"{n} hesap silindi."
    elif action == "approve":
        n = udb.bulk_set(ids, protect_id=acting["id"], is_approved=1, is_active=1)
        msg = f"{n} hesap onaylandı."
    elif action == "deactivate":
        n = udb.bulk_set(ids, protect_id=acting["id"], is_approved=0, is_active=0)
        msg = f"{n} hesap pasife alındı."
    else:
        return RedirectResponse(
            "/manufacturers?" + urlencode({"msg": "Geçersiz işlem.", "msg_type": "error"}), 303)

    skipped = len(ids) - n
    if skipped > 0:
        msg += f" ({skipped} hesap korumalı olduğu için atlandı.)"
    return RedirectResponse(
        "/manufacturers?" + urlencode({"msg": msg, "msg_type": "success" if n else "warning"}), 303)


@router.post("/add")
async def add_manufacturer(request: Request,
                           email: str = Form(...),
                           password: str = Form(...),
                           company_name: str = Form(""),
                           phone: str = Form("")):
    auth.require_admin(request)
    ok, reason = udb.create_user_by_admin(email, password, company_name, "manufacturer", phone)
    if ok:
        return RedirectResponse("/manufacturers?msg=Üretici+eklendi&msg_type=success", 303)
    return RedirectResponse("/manufacturers?msg=Bu+e-posta+zaten+kayıtlı&msg_type=error", 303)


@router.post("/approve")
async def approve_mfr(request: Request, id: int = Form(...)):
    auth.require_admin(request)
    udb.update_admin(id, is_approved=1, is_active=1)
    return RedirectResponse("/manufacturers", 303)


@router.post("/reject")
async def reject_mfr(request: Request, id: int = Form(...)):
    auth.require_admin(request)
    udb.update_admin(id, is_approved=0, is_active=0)
    return RedirectResponse("/manufacturers", 303)


@router.post("/save")
async def save_mfr(request: Request,
                   id: int = Form(...),
                   company_name: str = Form(""),
                   can_view_costs: int = Form(0),
                   senior_mode: int = Form(0),
                   is_admin: int = Form(0),
                   role: str = Form("manufacturer"),
                   is_approved: int = Form(0),
                   is_active: int = Form(0),
                   parent_id: int = Form(0)):
    acting = auth.require_admin(request)
    form = await request.form()
    allowed_menus = ",".join(form.getlist("allowed_menus"))
    allowed_categories = ",".join(form.getlist("allowed_categories"))
    allowed_actions = ",".join(form.getlist("allowed_actions"))
    allowed_models = ",".join(form.getlist("allowed_models"))
    udb.update_admin(
        id,
        company_name=company_name,
        can_view_costs=can_view_costs,
        senior_mode=senior_mode,
        role=role,
        is_approved=is_approved,
        is_active=is_active,
        allowed_menus=allowed_menus,
        allowed_categories=allowed_categories,
        parent_id=parent_id if parent_id else None,
        allowed_actions=allowed_actions,
        allowed_models=allowed_models,
    )
    # Yetki devri yalnızca gerçek yöneticiye ait
    if auth.is_true_admin(acting):
        udb.update_admin(id, is_admin=is_admin)
    if role == "dealer":
        return RedirectResponse("/dealers?msg=Kullanıcı+bayi+olarak+taşındı&msg_type=info", 303)
    return RedirectResponse("/manufacturers", 303)


@router.post("/delete")
async def delete_mfr(request: Request, id: int = Form(...)):
    auth.require_admin(request)
    udb.delete_user(id)
    return RedirectResponse("/manufacturers", 303)
