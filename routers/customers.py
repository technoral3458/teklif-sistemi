from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
import db.factory as fdb
import auth

router = APIRouter(prefix="/customers")
templates = Jinja2Templates(directory="templates")


@router.get("")
async def customers_list(request: Request, q: str = ""):
    user = auth.require_user(request)
    customers = fdb.get_customers()
    if q:
        ql = q.lower()
        customers = [
            c for c in customers
            if ql in (c.get("name") or "").lower() or ql in (c.get("email") or "").lower()
        ]
    balances = fdb.all_cust_balances()
    return templates.TemplateResponse("customers.html", {
        "request": request,
        "user": user,
        "customers": customers,
        "balances": balances,
        "q": q,
        "active_page": "customers",
    })


@router.post("/save")
async def save_customer(request: Request,
                        id: int = Form(0),
                        name: str = Form(...),
                        contact_person: str = Form(""),
                        email: str = Form(""),
                        phone: str = Form(""),
                        address: str = Form(""),
                        city: str = Form(""),
                        country: str = Form(""),
                        currency: str = Form("USD"),
                        notes: str = Form("")):
    user = auth.require_user(request)
    kw = dict(
        name=name, contact_person=contact_person, email=email,
        phone=phone, address=address, city=city, country=country,
        currency=currency, notes=notes,
    )
    if id:
        fdb.upd_customer(id, **kw)
    else:
        kw["dealer_id"] = user["id"]
        fdb.add_customer(**kw)
    return RedirectResponse("/customers", 303)


@router.post("/delete")
async def delete_customer(request: Request, id: int = Form(...)):
    auth.require_user(request)
    fdb.del_customer(id)
    return RedirectResponse("/customers", 303)
