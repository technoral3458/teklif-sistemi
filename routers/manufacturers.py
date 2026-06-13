from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
import db.users as udb
import db.factory as fdb
import auth

router = APIRouter(prefix="/manufacturers")
from tmpl import templates


@router.get("")
async def manufacturers_list(request: Request):
    user = auth.require_admin(request)
    manufacturers = [u for u in udb.all_users() if u["role"] == "manufacturer"]
    cats = fdb.get_cats()
    return templates.TemplateResponse(request, "manufacturers.html", {
        "user": user,
        "manufacturers": manufacturers,
        "categories": cats,
        "active_page": "manufacturers",
        "msg": request.query_params.get("msg"),
        "msg_type": request.query_params.get("msg_type", "info"),
    })


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
                   role: str = Form("manufacturer"),
                   is_approved: int = Form(0),
                   is_active: int = Form(0),
                   parent_id: int = Form(0)):
    auth.require_admin(request)
    form = await request.form()
    allowed_menus = ",".join(form.getlist("allowed_menus"))
    allowed_categories = ",".join(form.getlist("allowed_categories"))
    allowed_actions = ",".join(form.getlist("allowed_actions"))
    udb.update_admin(
        id,
        company_name=company_name,
        can_view_costs=can_view_costs,
        role=role,
        is_approved=is_approved,
        is_active=is_active,
        allowed_menus=allowed_menus,
        allowed_categories=allowed_categories,
        parent_id=parent_id if parent_id else None,
        allowed_actions=allowed_actions,
    )
    if role == "dealer":
        return RedirectResponse("/dealers?msg=Kullanıcı+bayi+olarak+taşındı&msg_type=info", 303)
    return RedirectResponse("/manufacturers", 303)


@router.post("/delete")
async def delete_mfr(request: Request, id: int = Form(...)):
    auth.require_admin(request)
    udb.delete_user(id)
    return RedirectResponse("/manufacturers", 303)
