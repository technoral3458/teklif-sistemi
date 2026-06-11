from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
import db.users as udb
import db.factory as fdb
import auth

router = APIRouter(prefix="/dealers")
from tmpl import templates


@router.get("")
async def dealers_list(request: Request):
    user = auth.require_admin(request)
    dealers = [u for u in udb.all_users() if u["role"] == "dealer"]
    cats = fdb.get_cats()
    return templates.TemplateResponse(request, "dealers.html", {
        "user": user,
        "dealers": dealers,
        "categories": cats,
        "active_page": "dealers",
        "msg": request.query_params.get("msg"),
        "msg_type": request.query_params.get("msg_type", "info"),
    })


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
                      role: str = Form("dealer"),
                      allowed_categories: str = Form("")):
    auth.require_admin(request)
    udb.update_admin(
        id,
        company_name=company_name,
        can_view_costs=can_view_costs,
        role=role,
        allowed_categories=allowed_categories,
    )
    if role == "manufacturer":
        return RedirectResponse("/manufacturers?msg=Kullanıcı+üretici+olarak+taşındı&msg_type=info", 303)
    return RedirectResponse("/dealers", 303)


@router.post("/delete")
async def delete_dealer(request: Request, id: int = Form(...)):
    auth.require_admin(request)
    udb.delete_user(id)
    return RedirectResponse("/dealers", 303)
