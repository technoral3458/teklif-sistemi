from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
import db.factory as fdb
import auth

router = APIRouter(prefix="/categories")
templates = Jinja2Templates(directory="templates")


@router.get("")
async def categories_list(request: Request):
    user = auth.require_user(request)
    cats = fdb.get_cats()
    return templates.TemplateResponse(request, "categories.html", {
        "user": user,
        "categories": cats,
        "active_page": "categories",
    })


@router.post("/save")
async def save_category(request: Request,
                        id: int = Form(0),
                        name: str = Form(...),
                        description: str = Form("")):
    auth.require_user(request)
    if id:
        fdb.upd_cat(id, name, description)
    else:
        fdb.add_cat(name, description)
    return RedirectResponse("/categories", 303)


@router.post("/delete")
async def delete_category(request: Request, id: int = Form(...)):
    auth.require_user(request)
    fdb.del_cat(id)
    return RedirectResponse("/categories", 303)
