from urllib.parse import urlencode

from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
import db.users as udb
import db.factory as fdb
import auth
import security

router = APIRouter(prefix="/dealers")
from tmpl import templates

# Bu puandan itibaren kayıt "şüpheli" sekmesinde listelenir.
SPAM_THRESHOLD = 3


@router.get("")
async def dealers_list(request: Request):
    user = auth.require_admin(request)
    # bayiler + üreticinin alt hesapları
    dealers = [u for u in udb.all_users()
               if u["role"] == "dealer" or (u["role"] == "manufacturer" and u.get("parent_id"))]

    # Bot kaydı şüphesi — aynı IP'den gelen yığın kayıtları da yakalar
    ip_counts = udb.reg_ip_counts()
    for d in dealers:
        d["spam_score"], d["spam_reasons"] = security.spam_score(d, ip_counts)
    suspicious = sorted(
        (d for d in dealers if d["spam_score"] >= SPAM_THRESHOLD),
        key=lambda d: -d["spam_score"],
    )

    manufacturers = udb.all_manufacturers()
    cats = fdb.get_cats()
    return templates.TemplateResponse(request, "dealers.html", {
        "user": user,
        "dealers": dealers,
        "suspicious": suspicious,
        "manufacturers": manufacturers,
        "categories": cats,
        "active_page": "dealers",
        "msg": request.query_params.get("msg"),
        "msg_type": request.query_params.get("msg_type", "info"),
    })


@router.post("/bulk")
async def bulk_dealers(request: Request):
    """Seçili hesapları topluca sil / onayla / pasife al.

    Her işlem db katmanında yeniden süzülür: yönetici rolündeki hesaplar ve
    işlemi yapanın kendisi, formdan ne gelirse gelsin listeye girmez.
    """
    acting = auth.require_admin(request)
    form = await request.form()
    ids = form.getlist("ids")
    action = (form.get("action") or "").strip()

    if not ids:
        return RedirectResponse(
            "/dealers?" + urlencode({"msg": "Hiç kayıt seçilmedi.", "msg_type": "warning"}), 303)

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
            "/dealers?" + urlencode({"msg": "Geçersiz işlem.", "msg_type": "error"}), 303)

    skipped = len(ids) - n
    if skipped > 0:
        msg += f" ({skipped} hesap korumalı olduğu için atlandı.)"
    return RedirectResponse(
        "/dealers?" + urlencode({"msg": msg, "msg_type": "success" if n else "warning"}), 303)


@router.post("/add")
async def add_dealer(request: Request,
                     email: str = Form(...),
                     password: str = Form(...),
                     company_name: str = Form(""),
                     phone: str = Form("")):
    auth.require_admin(request)
    ok, reason = udb.create_user_by_admin(email, password, company_name, "dealer", phone)
    if ok:
        return RedirectResponse("/dealers?msg=Bayi+eklendi&msg_type=success", 303)
    return RedirectResponse("/dealers?msg=Bu+e-posta+zaten+kayıtlı&msg_type=error", 303)


@router.post("/approve")
async def approve_dealer(request: Request, id: int = Form(...)):
    auth.require_admin(request)
    udb.update_admin(id, is_approved=1, is_active=1)
    return RedirectResponse("/dealers", 303)


@router.post("/reject")
async def reject_dealer(request: Request, id: int = Form(...)):
    auth.require_admin(request)
    udb.update_admin(id, is_approved=0, is_active=0)
    return RedirectResponse("/dealers", 303)


@router.post("/save")
async def save_dealer(request: Request,
                      id: int = Form(...),
                      company_name: str = Form(""),
                      can_view_costs: int = Form(0),
                      senior_mode: int = Form(0),
                      is_admin: int = Form(0),
                      role: str = Form("dealer"),
                      is_approved: int = Form(0),
                      is_active: int = Form(0),
                      parent_id: int = Form(0)):
    acting = auth.require_admin(request)
    form = await request.form()
    allowed_menus = ",".join(form.getlist("allowed_menus"))
    allowed_categories = ",".join(form.getlist("allowed_categories"))
    allowed_actions = ",".join(form.getlist("allowed_actions"))
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
    )
    # Yetki devri yalnızca gerçek yöneticiye ait
    if auth.is_true_admin(acting):
        udb.update_admin(id, is_admin=is_admin)
    if role == "manufacturer" and not parent_id:
        return RedirectResponse("/manufacturers?msg=Kullanıcı+üretici+olarak+taşındı&msg_type=info", 303)
    return RedirectResponse("/dealers", 303)


@router.post("/delete")
async def delete_dealer(request: Request, id: int = Form(...)):
    auth.require_admin(request)
    udb.delete_user(id)
    return RedirectResponse("/dealers", 303)
