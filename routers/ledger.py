import datetime

from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

import db.factory as fdb
import auth
from config import CURRENCIES, PAYMENT_METHODS

router = APIRouter(prefix="/ledger")
templates = Jinja2Templates(directory="templates")


@router.get("/customers")
async def cust_ledger_list(request: Request):
    user = auth.require_user(request)
    customers = fdb.get_customers()
    balances = fdb.all_cust_balances()
    return templates.TemplateResponse("ledger_customer_list.html", {
        "request": request,
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
    return templates.TemplateResponse("ledger_customer.html", {
        "request": request,
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


@router.get("/manufacturers")
async def mfr_ledger_list(request: Request):
    user = auth.require_user(request)
    all_txns = fdb.get_mtxns()
    mfr_names = list({t["manufacturer_name"] for t in all_txns})
    balances = {name: fdb.mfr_balance(name) for name in mfr_names}
    return templates.TemplateResponse("ledger_manufacturer_list.html", {
        "request": request,
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
    return templates.TemplateResponse("ledger_manufacturer.html", {
        "request": request,
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
