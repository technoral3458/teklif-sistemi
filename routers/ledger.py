import datetime

from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

import db.factory as fdb
import db.users as udb
import auth
from config import CURRENCIES, PAYMENT_METHODS

router = APIRouter(prefix="/ledger")
templates = Jinja2Templates(directory="templates")


@router.get("/customers")
async def cust_ledger_list(request: Request):
    user = auth.require_user(request)
    customers = fdb.get_customers()
    balances = fdb.all_cust_balances()
    return templates.TemplateResponse(request, "ledger_customer_list.html", {
        "user": user,
        "customers": customers,
        "balances": balances,
        "active_page": "ledger_customers",
    })


@router.get("/customers/{customer_id}")
async def cust_ledger(request: Request, customer_id: int):
    user = auth.require_user(request)
    customer = fdb.get_customer(customer_id)
    txns = fdb.get_ctxns(customer_id)
    balance = fdb.cust_balance(customer_id)
    return templates.TemplateResponse(request, "ledger_customer.html", {
        "user": user,
        "customer": customer,
        "txns": txns,
        "balance": balance,
        "currencies": CURRENCIES,
        "payment_methods": PAYMENT_METHODS,
        "active_page": "ledger_customers",
    })


@router.post("/customers/{customer_id}/add")
async def add_cust_txn(request: Request,
                       customer_id: int,
                       txn_type: str = Form(...),
                       amount: float = Form(...),
                       currency: str = Form("USD"),
                       description: str = Form(""),
                       payment_method: str = Form(""),
                       txn_date: str = Form("")):
    auth.require_user(request)
    if not txn_date:
        txn_date = datetime.date.today().isoformat()
    fdb.add_ctxn(customer_id, txn_type, amount, currency, description, payment_method, txn_date)
    return RedirectResponse(f"/ledger/customers/{customer_id}", 303)


@router.post("/customers/txn/delete")
async def del_cust_txn(request: Request,
                       id: int = Form(...),
                       customer_id: int = Form(...)):
    auth.require_user(request)
    fdb.del_ctxn(id)
    return RedirectResponse(f"/ledger/customers/{customer_id}", 303)


# ── Manufacturer User Ledger (user-id based) ─────────────────────────────────
# NOTE: these routes must come BEFORE /manufacturers/{mfr_name} to avoid conflict

@router.get("/manufacturers/users")
async def mfr_user_ledger_list(request: Request):
    user = auth.require_admin(request)
    manufacturers = [u for u in udb.all_users() if u["role"] == "manufacturer"]
    balances = fdb.all_mfr_user_balances()
    return templates.TemplateResponse(request, "ledger_mfr_user_list.html", {
        "user": user,
        "manufacturers": manufacturers,
        "balances": balances,
        "active_page": "ledger_manufacturers",
    })


@router.get("/manufacturers/users/{mfr_id}")
async def mfr_user_ledger(request: Request, mfr_id: int):
    user = auth.require_admin(request)
    manufacturer = udb.by_id(mfr_id)
    if not manufacturer:
        return RedirectResponse("/manufacturers", 303)
    txns = fdb.get_mfr_user_txns(mfr_id)
    balance = fdb.mfr_user_balance(mfr_id)
    return templates.TemplateResponse(request, "ledger_mfr_user.html", {
        "user": user,
        "manufacturer": manufacturer,
        "txns": txns,
        "balance": balance,
        "currencies": CURRENCIES,
        "payment_methods": PAYMENT_METHODS,
        "active_page": "ledger_manufacturers",
    })


@router.post("/manufacturers/users/{mfr_id}/add")
async def add_mfr_user_txn(request: Request, mfr_id: int,
                            txn_type: str = Form(...),
                            amount: float = Form(...),
                            currency: str = Form("USD"),
                            description: str = Form(""),
                            payment_method: str = Form(""),
                            txn_date: str = Form("")):
    auth.require_admin(request)
    if not txn_date:
        txn_date = datetime.date.today().isoformat()
    fdb.add_mfr_user_txn(mfr_id, txn_type, amount, currency, description, payment_method, txn_date)
    return RedirectResponse(f"/ledger/manufacturers/users/{mfr_id}", 303)


@router.post("/manufacturers/users/txn/delete")
async def del_mfr_user_txn(request: Request,
                            id: int = Form(...),
                            manufacturer_id: int = Form(...)):
    auth.require_admin(request)
    fdb.del_mfr_user_txn(id)
    return RedirectResponse(f"/ledger/manufacturers/users/{manufacturer_id}", 303)


# ── Manufacturer Name-based Ledger ────────────────────────────────────────────

@router.get("/manufacturers")
async def mfr_ledger_list(request: Request):
    user = auth.require_user(request)
    all_txns = fdb.get_mtxns()
    mfr_names = list({t["manufacturer_name"] for t in all_txns})
    balances = {name: fdb.mfr_balance(name) for name in mfr_names}
    return templates.TemplateResponse(request, "ledger_manufacturer_list.html", {
        "user": user,
        "manufacturers": mfr_names,
        "balances": balances,
        "all_txns": all_txns,
        "active_page": "ledger_manufacturers",
    })


@router.get("/manufacturers/{mfr_name}")
async def mfr_ledger(request: Request, mfr_name: str):
    user = auth.require_user(request)
    txns = fdb.get_mtxns(mfr_name)
    balance = fdb.mfr_balance(mfr_name)
    return templates.TemplateResponse(request, "ledger_manufacturer.html", {
        "user": user,
        "mfr_name": mfr_name,
        "txns": txns,
        "balance": balance,
        "currencies": CURRENCIES,
        "payment_methods": PAYMENT_METHODS,
        "active_page": "ledger_manufacturers",
    })


@router.post("/manufacturers/{mfr_name}/add")
async def add_mfr_txn(request: Request,
                      mfr_name: str,
                      txn_type: str = Form(...),
                      amount: float = Form(...),
                      currency: str = Form("USD"),
                      description: str = Form(""),
                      txn_date: str = Form("")):
    auth.require_user(request)
    if not txn_date:
        txn_date = datetime.date.today().isoformat()
    fdb.add_mtxn(mfr_name, txn_type, amount, currency, description, txn_date)
    return RedirectResponse(f"/ledger/manufacturers/{mfr_name}", 303)


@router.post("/manufacturers/txn/delete")
async def del_mfr_txn(request: Request,
                      id: int = Form(...),
                      mfr_name: str = Form(...)):
    auth.require_user(request)
    fdb.del_mtxn(id)
    return RedirectResponse(f"/ledger/manufacturers/{mfr_name}", 303)


# ── Dealer Ledger ─────────────────────────────────────────────────────────────

@router.get("/dealers")
async def dealer_ledger_list(request: Request):
    user = auth.require_admin(request)
    dealers = [u for u in udb.all_users() if u["role"] == "dealer"]
    balances = fdb.all_dealer_balances()
    return templates.TemplateResponse(request, "ledger_dealer_list.html", {
        "user": user,
        "dealers": dealers,
        "balances": balances,
        "active_page": "ledger_dealers",
    })


@router.get("/dealers/{dealer_id}")
async def dealer_ledger(request: Request, dealer_id: int):
    user = auth.require_admin(request)
    from db.users import by_id as user_by_id
    dealer = user_by_id(dealer_id)
    if not dealer:
        return RedirectResponse("/ledger/dealers", 303)
    txns = fdb.get_dealer_txns(dealer_id)
    balance = fdb.dealer_balance(dealer_id)
    return templates.TemplateResponse(request, "ledger_dealer.html", {
        "user": user,
        "dealer": dealer,
        "txns": txns,
        "balance": balance,
        "currencies": CURRENCIES,
        "payment_methods": PAYMENT_METHODS,
        "active_page": "ledger_dealers",
    })


@router.post("/dealers/{dealer_id}/add")
async def add_dealer_txn(request: Request, dealer_id: int,
                         txn_type: str = Form(...),
                         amount: float = Form(...),
                         currency: str = Form("USD"),
                         description: str = Form(""),
                         payment_method: str = Form(""),
                         txn_date: str = Form("")):
    auth.require_admin(request)
    if not txn_date:
        txn_date = datetime.date.today().isoformat()
    fdb.add_dealer_txn(dealer_id, txn_type, amount, currency, description, payment_method, txn_date)
    return RedirectResponse(f"/ledger/dealers/{dealer_id}", 303)


@router.post("/dealers/txn/delete")
async def del_dealer_txn(request: Request,
                         id: int = Form(...),
                         dealer_id: int = Form(...)):
    auth.require_admin(request)
    fdb.del_dealer_txn(id)
    return RedirectResponse(f"/ledger/dealers/{dealer_id}", 303)
