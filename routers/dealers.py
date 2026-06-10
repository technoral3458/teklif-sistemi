from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
import db.users as udb
import db.factory as fdb
import auth

router = APIRouter(prefix="/dealers")
templates = Jinja2Templates(directory="templates")


@router.get("")
async def dealers_list(request: Request):
    user = auth.require_admin(request)
    users = [u for u in udb.all_users() if u["role"] != "admin"]
    cats = fdb.get_cats()
    return templates.TemplateResponse("dealers.html", {
        "request": request,
        "user": user,
        "dealers": users,
        "categories": cats,
        "active_page": "dealers",
    })


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
    return RedirectResponse("/dealers", 303)


@router.post("/delete")
async def delete_dealer(request: Request, id: int = Form(...)):
    auth.require_admin(request)
    udb.delete_user(id)
    return RedirectResponse("/dealers", 303)
