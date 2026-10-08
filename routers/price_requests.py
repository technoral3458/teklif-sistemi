import threading

from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse

import db.factory as fdb
import db.users as udb
import auth

router = APIRouter(prefix="/price-requests")
from tmpl import templates


# ── Admin views ────────────────────────────────────────────────────────────────

@router.get("")
async def list_requests(request: Request, status: str = "pending"):
    user = auth.require_admin(request)
    reqs = fdb.get_price_requests(status=status if status != "all" else None)
    mfr_map = {m["id"]: m for m in udb.all_manufacturers()}
    for r in reqs:
        r["manufacturer"] = mfr_map.get(r["manufacturer_id"], {})
    return templates.TemplateResponse(request, "price_requests.html", {
        "user": user,
        "requests": reqs,
        "filter_status": status,
        "pending_count": fdb.pending_price_requests_count(),
        "active_page": "price_requests",
    })


@router.post("/{req_id}/approve")
async def approve_request(request: Request, req_id: int, admin_note: str = Form("")):
    auth.require_admin(request)
    req = fdb.get_price_request(req_id)
    if not req or req["status"] != "pending":
        return RedirectResponse("/price-requests?msg=Talep+bulunamadı&msg_type=error", 303)

    # Apply new price
    if req["entity_type"] == "model":
        fdb.upd_model(req["entity_id"],
                      purchase_price=req["new_price"],
                      purchase_currency=req["currency"])
    elif req["entity_type"] == "option":
        fdb.upd_option(req["entity_id"],
                       purchase_price=req["new_price"],
                       purchase_currency=req["currency"])

    fdb.resolve_price_request(req_id, "approved", admin_note)
    return RedirectResponse("/price-requests?msg=Onaylandı,+fiyat+güncellendi&msg_type=success", 303)


@router.post("/{req_id}/reject")
async def reject_request(request: Request, req_id: int, admin_note: str = Form("")):
    auth.require_admin(request)
    req = fdb.get_price_request(req_id)
    if not req or req["status"] != "pending":
        return RedirectResponse("/price-requests?msg=Talep+bulunamadı&msg_type=error", 303)
    fdb.resolve_price_request(req_id, "rejected", admin_note)
    return RedirectResponse("/price-requests?msg=Talep+reddedildi&msg_type=info", 303)


# ── Manufacturer: submit a price change request ────────────────────────────────

@router.post("/submit")
async def submit_request(request: Request,
                         entity_type: str = Form(...),
                         entity_id: int = Form(...),
                         new_price: float = Form(...),
                         currency: str = Form("USD"),
                         note: str = Form("")):
    user = auth.require_user(request)
    if user["role"] not in ("manufacturer", "admin"):
        return RedirectResponse("/", 303)

    import db.users as udb
    mfr_id = udb.effective_mfr_id(user) if hasattr(udb, "effective_mfr_id") else user["id"]

    # Get entity name and current purchase_price
    if entity_type == "model":
        entity = fdb.get_model(entity_id)
        entity_name = entity.get("name", "") if entity else ""
        current_price = float(entity.get("purchase_price") or 0) if entity else 0
    elif entity_type == "option":
        entity = fdb.get_option(entity_id)
        entity_name = entity.get("name", "") if entity else ""
        current_price = float(entity.get("purchase_price") or 0) if entity else 0
    else:
        return RedirectResponse("/", 303)

    if not entity:
        return RedirectResponse("/", 303)

    rid = fdb.add_price_request(
        entity_type=entity_type,
        entity_id=entity_id,
        entity_name=entity_name,
        manufacturer_id=mfr_id,
        current_price=current_price,
        new_price=new_price,
        currency=currency,
        note=note,
    )

    # Email admin (non-blocking)
    def _notify():
        try:
            from email_utils import send_admin_notification
            send_admin_notification("Fiyat Değişikliği Talebi", {
                "Varlık": f"{entity_type.capitalize()} — {entity_name}",
                "Mevcut Fiyat": f"{current_price:,.2f} {currency}",
                "Yeni Fiyat": f"{new_price:,.2f} {currency}",
                "Not": note or "—",
            })
        except Exception:
            pass
    threading.Thread(target=_notify, daemon=True).start()

    if entity_type == "model":
        redirect = f"/models/{entity_id}/edit?msg=Fiyat+talebi+gönderildi&msg_type=success"
    else:
        redirect = "/options?msg=Fiyat+talebi+gönderildi&msg_type=success"
    return RedirectResponse(redirect, 303)


# ── Manufacturer: view own requests ───────────────────────────────────────────

@router.get("/mine")
async def my_requests(request: Request):
    user = auth.require_user(request)
    import db.users as udb
    mfr_id = udb.effective_mfr_id(user) if hasattr(udb, "effective_mfr_id") else user["id"]
    reqs = fdb.get_price_requests(manufacturer_id=mfr_id)
    return templates.TemplateResponse(request, "price_requests_mine.html", {
        "user": user,
        "requests": reqs,
        "active_page": "price_requests",
    })
