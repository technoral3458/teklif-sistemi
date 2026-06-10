from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
import db.users as udb
import db.factory as fdb
import auth

router = APIRouter(prefix="/manufacturers")
templates = Jinja2Templates(directory="templates")


@router.get("")
async def manufacturers_list(request: Request):
    user = auth.require_admin(request)
    users = [u for u in udb.all_users() if u["role"] == "manufacturer"]
    cats = fdb.get_cats()
    return templates.TemplateResponse(request, "manufacturers.html", {
        "user": user,
        "manufacturers": users,
        "categories": cats,
        "active_page": "ledger_manufacturers",
    })


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
                   allowed_categories: str = Form("")):
    auth.require_admin(request)
    udb.update_admin(id,
        company_name=company_name,
        can_view_costs=can_view_costs,
        allowed_categories=allowed_categories,
    )
    return RedirectResponse("/manufacturers", 303)


@router.post("/delete")
async def delete_mfr(request: Request, id: int = Form(...)):
    auth.require_admin(request)
    udb.delete_user(id)
    return RedirectResponse("/manufacturers", 303)
