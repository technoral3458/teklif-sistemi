import datetime
import threading
from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse

import db.factory as fdb
import db.users as udb
import auth
from config import CURRENCIES, PAYMENT_METHODS

router = APIRouter(prefix="/orders")
from tmpl import templates


def _notify(event_label: str, details: dict):
    """Fire-and-forget admin email notification."""
    def _send():
        try:
            from email_utils import send_admin_notification
            send_admin_notification(event_label, details)
        except Exception:
            pass
    threading.Thread(target=_send, daemon=True).start()


def _enrich(orders):
    customers = {c["id"]: c for c in fdb.get_customers()}
    models    = {m["id"]: m for m in fdb.get_models()}
    mfr_users = {u["id"]: u for u in udb.all_users() if u["role"] == "manufacturer"}
    dealer_users = {u["id"]: u for u in udb.all_users() if u["role"] == "dealer"}
    for o in orders:
        c = customers.get(o["customer_id"]) or {}
        m = models.get(o["model_id"]) or {}
        o["customer_name"] = c.get("name", "-")
        o["model_name"]    = m.get("name", "-")
        mfr = mfr_users.get(o.get("manufacturer_id"))
        o["manufacturer_name"] = mfr["company_name"] if mfr else "-"
        dlr = dealer_users.get(o.get("dealer_id"))
        o["dealer_name"] = dlr["company_name"] if dlr else "-"
    return orders


@router.get("")
async def orders_list(request: Request):
    user = auth.require_user(request)
    role = user["role"]
    if role == "admin":
        orders = fdb.get_offers(status="Sipariş Verildi")
        for s in ["Admin Onaylı", "Üretimde", "Tamamlandı", "Teslim Edildi"]:
            orders += fdb.get_offers(status=s)
    elif role == "manufacturer":
        mfr_id = udb.effective_mfr_id(user)
        orders = [o for o in fdb.get_offers() if o.get("manufacturer_id") == mfr_id and o.get("status") not in ("Beklemede",)]
    elif role == "dealer":
        orders = fdb.get_offers(dealer_id=user["id"])
        orders = [o for o in orders if o["status"] not in ("Beklemede",)]
    else:
        orders = []
    orders = _enrich(orders)
    manufacturers = [u for u in udb.all_users() if u["role"] == "manufacturer"]
    return templates.TemplateResponse(request, "orders.html", {
        "user": user,
        "orders": orders,
        "manufacturers": manufacturers,
        "active_page": "orders",
    })


@router.get("/{oid}")
async def order_detail(request: Request, oid: int):
    user = auth.require_user(request)
    offer = fdb.get_offer(oid)
    if not offer:
        return RedirectResponse("/orders", 303)
    items = fdb.get_offer_items(oid)
    options = {o["id"]: o for o in fdb.get_options()}
    for it in items:
        opt = options.get(it["option_id"]) or {}
        it["option_name"] = opt.get("name", "-")
    stages = fdb.get_order_stages(oid)
    customers = {c["id"]: c for c in fdb.get_customers()}
    models    = {m["id"]: m for m in fdb.get_models()}
    mfr_users = {u["id"]: u for u in udb.all_users() if u["role"] == "manufacturer"}
    dealer_users = {u["id"]: u for u in udb.all_users() if u["role"] in ("dealer","admin")}
    customer = customers.get(offer["customer_id"]) or {}
    model    = models.get(offer["model_id"]) or {}
    mfr      = mfr_users.get(offer.get("manufacturer_id"))
    dlr      = dealer_users.get(offer.get("dealer_id"))
    offer["customer_name"]     = customer.get("name", "-")
    offer["model_name"]        = model.get("name", "-")
    offer["manufacturer_name"] = mfr["company_name"] if mfr else "-"
    offer["dealer_name"]       = dlr["company_name"] if dlr else "-"
    manufacturers = list(mfr_users.values())
    mfr_id = udb.effective_mfr_id(user)
    # default manufacturer comes from model if not yet assigned
    default_mfr_id = model.get("manufacturer_id") or 0
    return templates.TemplateResponse(request, "order_detail.html", {
        "user": user,
        "offer": offer,
        "items": items,
        "stages": stages,
        "manufacturers": manufacturers,
        "default_mfr_id": default_mfr_id,
        "currencies": CURRENCIES,
        "payment_methods": PAYMENT_METHODS,
        "active_page": "orders",
        "effective_mfr_id": mfr_id,
        "can_confirm": udb.has_action(user, "order_confirm"),
        "can_status":  udb.has_action(user, "order_status"),
        "can_stage":   udb.has_action(user, "order_stage"),
        "show_prices": user["role"] != "manufacturer",
    })


@router.post("/{oid}/approve")
async def approve_order(request: Request, oid: int,
                        manufacturer_id: int = Form(...),
                        admin_notes: str = Form("")):
    auth.require_admin(request)
    fdb.approve_order(oid, manufacturer_id, admin_notes)
    offer = fdb.get_offer(oid)
    _notify("Admin Siparişi Onayladı", {
        "Sipariş No": f"#{oid}",
        "Müşteri": (offer or {}).get("customer_name", "-"),
        "Notlar": admin_notes or "-",
    })
    return RedirectResponse(f"/orders/{oid}", 303)


@router.post("/{oid}/reject")
async def reject_order(request: Request, oid: int,
                       admin_notes: str = Form("")):
    auth.require_admin(request)
    fdb.reject_order(oid, admin_notes)
    return RedirectResponse(f"/orders/{oid}", 303)


@router.post("/{oid}/confirm")
async def confirm_order(request: Request, oid: int,
                        termin_date: str = Form(""),
                        mfr_notes: str = Form("")):
    user = auth.require_user(request)
    if not udb.has_action(user, "order_confirm"):
        return RedirectResponse(f"/orders/{oid}", 303)
    offer = fdb.get_offer(oid)
    mfr_id = udb.effective_mfr_id(user)
    if offer and offer.get("manufacturer_id") == mfr_id:
        fdb.mfr_confirm_order(oid, termin_date, mfr_notes)
        _notify("Üretici Siparişi Onayladı", {
            "Sipariş No": f"#{oid}",
            "Üretici": user.get("company_name", "-"),
            "Termin": termin_date or "-",
            "Not": mfr_notes or "-",
        })
    return RedirectResponse(f"/orders/{oid}", 303)


@router.post("/{oid}/status")
async def update_status(request: Request, oid: int,
                        mfr_status: str = Form(...)):
    user = auth.require_user(request)
    if not udb.has_action(user, "order_status") and user["role"] != "admin":
        return RedirectResponse(f"/orders/{oid}", 303)
    offer = fdb.get_offer(oid)
    mfr_id = udb.effective_mfr_id(user)
    if offer and (offer.get("manufacturer_id") == mfr_id or user["role"] == "admin"):
        fdb.update_mfr_status(oid, mfr_status)
        status_labels = {
            "in_production": "Üretimde",
            "completed": "Tamamlandı",
            "delivered": "Teslim Edildi",
        }
        _notify("Sipariş Durumu Güncellendi", {
            "Sipariş No": f"#{oid}",
            "Üretici": user.get("company_name", "-"),
            "Yeni Durum": status_labels.get(mfr_status, mfr_status),
        })
    return RedirectResponse(f"/orders/{oid}", 303)


@router.post("/{oid}/stage")
async def add_stage(request: Request, oid: int,
                    stage_name: str = Form(""),
                    notes: str = Form(""),
                    stage_date: str = Form("")):
    user = auth.require_user(request)
    if not udb.has_action(user, "order_stage") and user["role"] != "admin":
        return RedirectResponse(f"/orders/{oid}", 303)
    offer = fdb.get_offer(oid)
    mfr_id = udb.effective_mfr_id(user)
    if offer and (offer.get("manufacturer_id") == mfr_id or user["role"] == "admin"):
        if not stage_date:
            stage_date = datetime.date.today().isoformat()
        fdb.add_order_stage(oid, stage_name, notes, stage_date)
        _notify("Üretim Aşaması Eklendi", {
            "Sipariş No": f"#{oid}",
            "Üretici": user.get("company_name", "-"),
            "Aşama": stage_name,
            "Tarih": stage_date,
            "Not": notes or "-",
        })
    return RedirectResponse(f"/orders/{oid}", 303)


@router.post("/stage/delete")
async def del_stage(request: Request,
                    id: int = Form(...),
                    order_id: int = Form(...)):
    auth.require_user(request)
    fdb.del_order_stage(id)
    return RedirectResponse(f"/orders/{order_id}", 303)
