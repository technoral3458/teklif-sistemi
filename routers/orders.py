import datetime
import os
import uuid
import threading
from fastapi import APIRouter, Request, Form, UploadFile, File
from fastapi.responses import RedirectResponse
from typing import Optional

import db.factory as fdb
import db.users as udb
import auth
from config import CURRENCIES, PAYMENT_METHODS, IMAGES_DIR, DOCS_DIR

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
    mfr_users = {u["id"]: u for u in udb.all_manufacturers()}
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
    elif auth.is_mfr(user):
        mfr_id = udb.effective_mfr_id(user)
        orders = [o for o in fdb.get_offers() if o.get("manufacturer_id") == mfr_id and o.get("status") not in ("Beklemede",)]
    elif role == "dealer":
        orders = fdb.get_offers(dealer_id=user["id"])
        orders = [o for o in orders if o["status"] not in ("Beklemede",)]
    else:
        orders = []
    orders = _enrich(orders)
    manufacturers = udb.all_manufacturers()
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
    lang = user.get("lang", "tr")
    for it in items:
        opt = options.get(it["option_id"]) or {}
        name_key = f"name_{lang}" if lang != "tr" else "name"
        it["option_name"] = opt.get(name_key) or opt.get("name", "-")
    stages = fdb.get_order_stages(oid)
    customers = {c["id"]: c for c in fdb.get_customers()}
    models    = {m["id"]: m for m in fdb.get_models()}
    mfr_users = {u["id"]: u for u in udb.all_manufacturers()}
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
    steps = fdb.get_production_steps()
    proformas = fdb.get_order_proformas(oid)
    documents = fdb.get_order_documents(oid)
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
        "production_steps": steps,
        "proformas": proformas,
        "documents": documents,
    })


@router.get("/{oid}/production-pdf")
async def production_pdf(request: Request, oid: int, dl: int = 0):
    user = auth.require_user(request)
    offer = fdb.get_offer(oid)
    if not offer:
        return RedirectResponse("/orders", 303)
    mfr_id = udb.effective_mfr_id(user)
    if user["role"] != "admin" and offer.get("manufacturer_id") != mfr_id:
        return RedirectResponse("/orders", 303)

    lang = user.get("lang", "tr")
    items = fdb.get_offer_items(oid)
    opts = {o["id"]: o for o in fdb.get_options()}

    for item in items:
        opt = opts.get(item.get("option_id"), {})
        item["option_name"] = (opt.get(f"name_{lang}") or opt.get("name", "-")) if lang != "tr" else opt.get("name", "-")
        item["description"] = (opt.get(f"description_{lang}") or opt.get("description", "")) if lang != "tr" else opt.get("description", "")
        item["image_path"] = opt.get("image_path", "") or ""

    model = fdb.get_model(offer["model_id"]) if offer.get("model_id") else {}
    model = model or {}
    model_name = (model.get(f"name_{lang}") or model.get("name") or "") if lang != "tr" else (model.get("name") or "")

    from routers.offers import _best_display_image, _parse_specs, _filter_specs
    display_image = _best_display_image(model, offer, items, opts)
    specs = _filter_specs(_parse_specs(model, lang), items, opts)

    company = fdb.get_company() or {}
    mfr_map = {u["id"]: u for u in udb.all_manufacturers()}
    mfr = mfr_map.get(offer.get("manufacturer_id"))
    offer["manufacturer_name"] = mfr["company_name"] if mfr else "-"
    customer = fdb.get_customer(offer["customer_id"]) if offer.get("customer_id") else {}
    offer["customer_name"] = (customer or {}).get("name", "-")

    _L = {
        "tr": {
            "title": "ÜRETİM EMRİ",
            "order_no": "Sipariş No", "date": "Tarih",
            "manufacturer": "Üretici", "model": "Model",
            "qty": "Adet", "deadline": "Termin",
            "machine_specs": "MAKİNE STANDART ÖZELLİKLERİ",
            "std_features": "Standart Özellikler",
            "selected_options": "SEÇİLEN OPSİYONLAR VE DONANIM",
            "option_img": "Görsel", "option_desc": "Donanım Açıklaması",
            "option_qty": "Adet", "notes": "Notlar",
            "summary_title": "ÜRETİM EMRİ ÖZETİ",
            "included_options": "Dahil Opsiyonlar / Donanımlar",
            "pcs": "adet",
            "footer": "Bu üretim emri üretici onayı için düzenlenmiştir.",
            "customer": "Müşteri",
        },
        "en": {
            "title": "PRODUCTION ORDER",
            "order_no": "Order No", "date": "Date",
            "manufacturer": "Manufacturer", "model": "Model",
            "qty": "Quantity", "deadline": "Deadline",
            "machine_specs": "STANDARD MACHINE SPECIFICATIONS",
            "std_features": "Standard Features",
            "selected_options": "SELECTED OPTIONS & EQUIPMENT",
            "option_img": "Image", "option_desc": "Equipment Description",
            "option_qty": "Qty", "notes": "Notes",
            "summary_title": "PRODUCTION ORDER SUMMARY",
            "included_options": "Included Options / Equipment",
            "pcs": "pcs",
            "footer": "This production order has been prepared for manufacturer approval.",
            "customer": "Customer",
        },
        "zh": {
            "title": "生产工单",
            "order_no": "订单编号", "date": "日期",
            "manufacturer": "制造商", "model": "型号",
            "qty": "数量", "deadline": "交货期",
            "machine_specs": "机器标准规格",
            "std_features": "标准特性",
            "selected_options": "已选配件与设备",
            "option_img": "图片", "option_desc": "设备描述",
            "option_qty": "数量", "notes": "备注",
            "summary_title": "生产工单摘要",
            "included_options": "包含配件/设备",
            "pcs": "件",
            "footer": "本生产工单已准备好等待制造商确认。",
            "customer": "客户",
        },
    }
    lbl = _L.get(lang, _L["tr"])

    from fastapi.responses import Response as _R
    html_str = templates.get_template("production_order_pdf.html").render({
        "offer": offer, "items": items, "model": model,
        "model_name": model_name, "specs": specs,
        "display_image": display_image, "company": company,
        "lang": lang, "lbl": lbl,
    })
    from weasyprint import HTML as WH
    pdf_bytes = WH(string=html_str, base_url="http://127.0.0.1:8501/").write_pdf()
    fname = f"UretimEmri_{offer['offer_no']}.pdf"
    disposition = "attachment" if dl else "inline"
    return _R(pdf_bytes, media_type="application/pdf",
              headers={"Content-Disposition": f'{disposition}; filename="{fname}"'})


@router.post("/{oid}/approve")
async def approve_order(request: Request, oid: int,
                        manufacturer_id: int = Form(0),
                        admin_notes: str = Form("")):
    auth.require_admin(request)
    if not manufacturer_id:
        offer = fdb.get_offer(oid)
        model = fdb.get_model(offer["model_id"]) if offer else None
        manufacturer_id = (model or {}).get("manufacturer_id") or 0
    fdb.approve_order(oid, manufacturer_id or None, admin_notes)
    offer = fdb.get_offer(oid)
    _notify("Admin Siparişi Onayladı", {
        "Sipariş No": f"#{oid}",
        "Müşteri": (offer or {}).get("customer_name", "-"),
        "Notlar": admin_notes or "-",
    })
    return RedirectResponse(f"/orders/{oid}", 303)


@router.post("/{oid}/reassign")
async def reassign_manufacturer(request: Request, oid: int,
                                manufacturer_id: int = Form(0)):
    auth.require_admin(request)
    if manufacturer_id:
        fdb.reassign_order_manufacturer(oid, manufacturer_id)
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
                        mfr_notes: str = Form(""),
                        serial_number: str = Form("")):
    user = auth.require_user(request)
    if not udb.has_action(user, "order_confirm"):
        return RedirectResponse(f"/orders/{oid}", 303)
    offer = fdb.get_offer(oid)
    mfr_id = udb.effective_mfr_id(user)
    if offer and offer.get("manufacturer_id") == mfr_id:
        fdb.mfr_confirm_order(oid, termin_date, mfr_notes, serial_number)
        _notify("Üretici Siparişi Onayladı", {
            "Sipariş No": f"#{oid}",
            "Üretici": user.get("company_name", "-"),
            "Termin": termin_date or "-",
            "Not": mfr_notes or "-",
        })
    return RedirectResponse(f"/orders/{oid}", 303)


@router.post("/{oid}/status")
async def update_status(request: Request, oid: int,
                        mfr_status: str = Form(...),
                        mfr_status_date: str = Form("")):
    user = auth.require_user(request)
    if not udb.has_action(user, "order_status") and user["role"] != "admin":
        return RedirectResponse(f"/orders/{oid}", 303)
    offer = fdb.get_offer(oid)
    mfr_id = udb.effective_mfr_id(user)
    if offer and (offer.get("manufacturer_id") == mfr_id or user["role"] == "admin"):
        fdb.update_mfr_status(oid, mfr_status, mfr_status_date)
        steps = fdb.get_production_steps(active_only=False)
        step = next((s for s in steps if s["code"] == mfr_status), None)
        status_label = step["label_tr"] if step else mfr_status
        _notify("Sipariş Durumu Güncellendi", {
            "Sipariş No": f"#{oid}",
            "Üretici": user.get("company_name", "-"),
            "Yeni Durum": status_label,
        })
    return RedirectResponse(f"/orders/{oid}", 303)


@router.post("/{oid}/stage")
async def add_stage(request: Request, oid: int,
                    stage_name: str = Form(""),
                    notes: str = Form(""),
                    stage_date: str = Form(""),
                    photo: Optional[UploadFile] = File(None)):
    user = auth.require_user(request)
    if not udb.has_action(user, "order_stage") and user["role"] != "admin":
        return RedirectResponse(f"/orders/{oid}", 303)
    offer = fdb.get_offer(oid)
    mfr_id = udb.effective_mfr_id(user)
    if offer and (offer.get("manufacturer_id") == mfr_id or user["role"] == "admin"):
        if not stage_date:
            stage_date = datetime.date.today().isoformat()
        photo_path = ""
        if photo and photo.filename:
            ext = os.path.splitext(photo.filename)[1].lower() or ".jpg"
            fname = f"stage_{oid}_{uuid.uuid4().hex[:8]}{ext}"
            os.makedirs(IMAGES_DIR, exist_ok=True)
            content = await photo.read()
            with open(os.path.join(IMAGES_DIR, fname), "wb") as f:
                f.write(content)
            photo_path = f"img/uploads/{fname}"
        fdb.add_order_stage(oid, stage_name, notes, stage_date, photo_path)
        _notify("Üretim Aşaması Eklendi", {
            "Sipariş No": f"#{oid}",
            "Üretici": user.get("company_name", "-"),
            "Aşama": stage_name,
            "Tarih": stage_date,
            "Not": notes or "-",
        })
    return RedirectResponse(f"/orders/{oid}", 303)


@router.post("/proforma/delete")
async def delete_proforma(request: Request, id: int = Form(...), order_id: int = Form(...)):
    user = auth.require_user(request)
    offer = fdb.get_offer(order_id)
    mfr_id = udb.effective_mfr_id(user)
    if user["role"] != "admin" and (not offer or offer.get("manufacturer_id") != mfr_id):
        return RedirectResponse("/orders", 303)
    import os as _os
    from config import BASE_DIR as _BASE
    fpath = fdb.del_order_proforma(id)
    if fpath:
        full = _os.path.join(_BASE, "static", fpath)
        if _os.path.exists(full):
            _os.remove(full)
    return RedirectResponse(f"/orders/{order_id}", 303)


@router.post("/document/delete")
async def delete_document(request: Request, id: int = Form(...), order_id: int = Form(...)):
    user = auth.require_user(request)
    offer = fdb.get_offer(order_id)
    mfr_id = udb.effective_mfr_id(user)
    if user["role"] != "admin" and (not offer or offer.get("manufacturer_id") != mfr_id):
        return RedirectResponse("/orders", 303)
    import os as _os
    from config import BASE_DIR as _BASE
    fpath = fdb.del_order_document(id)
    if fpath:
        full = _os.path.join(_BASE, "static", fpath)
        if _os.path.exists(full):
            _os.remove(full)
    return RedirectResponse(f"/orders/{order_id}", 303)


@router.post("/stage/delete")
async def del_stage(request: Request,
                    id: int = Form(...),
                    order_id: int = Form(...)):
    auth.require_user(request)
    fdb.del_order_stage(id)
    return RedirectResponse(f"/orders/{order_id}", 303)


@router.post("/{oid}/proforma")
async def upload_proforma(request: Request, oid: int,
                          proforma_file: UploadFile = File(...)):
    user = auth.require_user(request)
    offer = fdb.get_offer(oid)
    if not offer:
        return RedirectResponse("/orders", 303)
    mfr_id = udb.effective_mfr_id(user)
    if user["role"] != "admin" and offer.get("manufacturer_id") != mfr_id:
        return RedirectResponse("/orders", 303)
    if not proforma_file or not proforma_file.filename:
        return RedirectResponse(f"/orders/{oid}", 303)
    import os as _os
    ext = _os.path.splitext(proforma_file.filename)[1].lower() or ".pdf"
    fname = f"proforma_{oid}_{uuid.uuid4().hex[:8]}{ext}"
    dest = _os.path.join(DOCS_DIR, fname)
    _os.makedirs(DOCS_DIR, exist_ok=True)
    content = await proforma_file.read()
    with open(dest, "wb") as f:
        f.write(content)
    fdb.add_order_proforma(oid, f"docs/{fname}", proforma_file.filename, user["id"])
    return RedirectResponse(f"/orders/{oid}", 303)


@router.post("/{oid}/document")
async def upload_document(request: Request, oid: int,
                           doc_file: UploadFile = File(...),
                           doc_type: str = Form("")):
    user = auth.require_user(request)
    offer = fdb.get_offer(oid)
    if not offer:
        return RedirectResponse("/orders", 303)
    mfr_id = udb.effective_mfr_id(user)
    if user["role"] != "admin" and offer.get("manufacturer_id") != mfr_id:
        return RedirectResponse("/orders", 303)
    if not doc_file or not doc_file.filename:
        return RedirectResponse(f"/orders/{oid}", 303)
    import os as _os
    ext = _os.path.splitext(doc_file.filename)[1].lower() or ".pdf"
    fname = f"doc_{oid}_{uuid.uuid4().hex[:8]}{ext}"
    dest = _os.path.join(DOCS_DIR, fname)
    _os.makedirs(DOCS_DIR, exist_ok=True)
    content = await doc_file.read()
    with open(dest, "wb") as f:
        f.write(content)
    fdb.add_order_document(oid, f"docs/{fname}", doc_file.filename, doc_type, user["id"])
    return RedirectResponse(f"/orders/{oid}", 303)


@router.post("/{oid}/serial")
async def set_serial(request: Request, oid: int, serial_number: str = Form("")):
    user = auth.require_user(request)
    offer = fdb.get_offer(oid)
    if not offer:
        return RedirectResponse("/orders", 303)
    mfr_id = udb.effective_mfr_id(user)
    if user["role"] != "admin" and offer.get("manufacturer_id") != mfr_id:
        return RedirectResponse("/orders", 303)
    fdb.set_order_serial(oid, serial_number.strip())
    return RedirectResponse(f"/orders/{oid}", 303)
