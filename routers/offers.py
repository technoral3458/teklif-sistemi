import json
import os
import uuid
import datetime
import threading

from fastapi import APIRouter, Request, Form, UploadFile, File
from fastapi.responses import RedirectResponse, Response
from typing import Optional

import db.factory as fdb
import auth
from config import OFFER_STATUSES, CURRENCIES, BASE_DIR, CONTRACTS_DIR

router = APIRouter(prefix="/offers")
from tmpl import templates


def _filter_specs(specs, items, opts):
    """Hide standard specs that are replaced by selected options with a conflict_group."""
    hidden = set()
    for item in items:
        opt = opts.get(item.get("option_id"), {})
        if not opt.get("conflict_group"):
            continue
        # Match by option name or conflict_group value (case-insensitive)
        for key in (opt.get("name") or "", opt.get("conflict_group") or ""):
            k = key.lower().strip()
            if k:
                hidden.add(k)
    if not hidden:
        return specs
    return [s for s in specs if s.get("title", "").lower().strip() not in hidden]


def _resolve_opt_fields(item, opt, lang):
    """Set language-aware fields on an offer item from its option."""
    item["option_name"] = (opt.get(f"name_{lang}") or opt.get("name", "-")) if lang != "tr" else opt.get("name", "-")
    item["description"] = (opt.get(f"description_{lang}") or opt.get("description", "")) if lang != "tr" else (opt.get("description", "") or "")
    item["image_path"]  = opt.get("image_path", "") or ""
    item["video_url"]   = opt.get("video_url", "") or ""


def _best_display_image(model, offer, items, opts):
    """Return the best image path for an offer.

    Priority order (highest wins):
      - Option variation images (opt.image_priority)
      - Line-variant image matching offer.machine_count (treated as priority=100 baseline)
      - Model's main image (fallback)
    """
    best_prio = -1
    display_image = (model.get("image_path", "") if model else "")

    # Check option variation images
    for item in items:
        opt = opts.get(item.get("option_id"), {})
        var_img = opt.get("variation_image_path", "")
        prio = opt.get("image_priority") or 0
        if var_img and prio > best_prio:
            display_image, best_prio = var_img, prio

    # Check line-machine variant image for selected machine_count
    if model and model.get("is_line") and offer:
        mc = offer.get("machine_count") or 1
        line_imgs = fdb.get_model_line_images(model["id"])
        for li in line_imgs:
            if li["line_count"] == mc and li.get("image_path"):
                line_prio = (li.get("priority") or 0) + 100  # offset so explicit priority wins
                if line_prio > best_prio:
                    display_image, best_prio = li["image_path"], line_prio

    return display_image


def _parse_specs(model, lang):
    """Return parsed specs list for the given language."""
    if not model:
        return []
    if lang != "tr":
        raw = (model.get(f"specs_{lang}", "") or model.get("specs", "")) or ""
    else:
        raw = (model.get("specs", "") or "")
    raw = raw.strip()
    if raw.startswith("["):
        try:
            return json.loads(raw)
        except Exception:
            pass
    elif raw.startswith("{"):
        try:
            obj = json.loads(raw)
            return [{"title": k, "desc": str(v), "img": ""} for k, v in obj.items()]
        except Exception:
            pass
    return []


@router.get("")
async def offers_list(request: Request, status: str = "", q: str = ""):
    user = auth.require_user(request)
    _dl = None if user["role"] == "admin" else user["id"]
    offers = fdb.get_offers(status=status or None, dealer_id=_dl)
    customers = {c["id"]: c for c in fdb.get_customers(dealer_id=_dl)}
    models = {m["id"]: m for m in fdb.get_models()}
    for o in offers:
        o["customer_name"] = customers.get(o.get("customer_id"), {}).get("name", "-")
        o["model_name"] = models.get(o.get("model_id"), {}).get("name", "-")
    if q:
        ql = q.lower()
        offers = [
            o for o in offers
            if ql in (o.get("offer_no") or "").lower()
            or ql in (o.get("customer_name") or "").lower()
        ]
    return templates.TemplateResponse(request, "offers.html", {
        "user": user,
        "offers": offers,
        "statuses": OFFER_STATUSES,
        "selected_status": status,
        "q": q,
        "active_page": "offers",
    })


@router.get("/new")
async def offer_new(request: Request):
    user = auth.require_user(request)
    _cust_dealer = None if user["role"] == "admin" else user["id"]
    customers = fdb.get_customers(dealer_id=_cust_dealer)
    cats = fdb.get_cats()
    models = fdb.get_models()
    options = fdb.get_options()
    cat_map = {c["id"]: c["name"] for c in cats}
    for m in models:
        m["category_name"] = cat_map.get(m.get("category_id"), "-")
        compat = []
        if m.get("compatible_options"):
            try:
                compat = json.loads(m["compatible_options"])
            except Exception:
                pass
        m["compatible_options_list"] = compat
        m["line_images_map"] = {img["line_count"]: img for img in fdb.get_model_line_images(m["id"])}
    delivery_terms = fdb.get_delivery_terms(active_only=True)
    return templates.TemplateResponse(request, "offer_wizard.html", {
        "user": user,
        "customers": customers,
        "categories": cats,
        "models": models,
        "options": options,
        "currencies": CURRENCIES,
        "delivery_terms": delivery_terms,
        "active_page": "offers",
    })


@router.post("/create")
async def create_offer(request: Request,
                       customer_id: int = Form(0),
                       new_customer_name: str = Form(""),
                       new_customer_contact: str = Form(""),
                       new_customer_email: str = Form(""),
                       new_customer_phone: str = Form(""),
                       model_id: int = Form(...),
                       machine_count: int = Form(1),
                       currency: str = Form("USD"),
                       discount_pct: float = Form(0.0),
                       delivery_term_id: int = Form(0),
                       notes: str = Form(""),
                       validity_date: str = Form(""),
                       delivery_method: str = Form(""),
                       delivery_time: str = Form(""),
                       logistics: str = Form(""),
                       payment_notes: str = Form(""),
                       options_json: str = Form("[]")):
    user = auth.require_user(request)

    if not customer_id and new_customer_name.strip():
        customer_id = fdb.add_customer(
            name=new_customer_name.strip(),
            contact_person=new_customer_contact,
            email=new_customer_email,
            phone=new_customer_phone,
            dealer_id=user["id"],
        )

    model = fdb.get_model(model_id)
    base_price = float(model["base_price"]) if model else 0.0

    selected_options = []
    try:
        selected_options = json.loads(options_json)
    except Exception:
        pass

    options_total = sum(float(o.get("line_total", 0)) for o in selected_options)
    subtotal = base_price * machine_count + options_total

    term = fdb.get_delivery_term(delivery_term_id) if delivery_term_id else None
    delivery_term_discount = float(term["discount_pct"]) if term else 0.0
    total_price = subtotal * (1 - delivery_term_discount / 100) * (1 - discount_pct / 100)

    offer_no = f"TKL-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"

    offer_id = fdb.create_offer(
        offer_no=offer_no,
        customer_id=customer_id,
        model_id=model_id,
        machine_count=machine_count,
        currency=currency,
        base_price=base_price,
        options_total=options_total,
        discount_pct=discount_pct,
        total_price=total_price,
        status="Beklemede",
        notes=notes,
        validity_date=validity_date,
        delivery_method=delivery_method,
        delivery_time=delivery_time,
        logistics=logistics,
        payment_notes=payment_notes,
        dealer_id=user["id"],
        delivery_term_id=delivery_term_id or None,
        delivery_term_discount=delivery_term_discount,
    )

    if selected_options:
        items = [
            {
                "option_id": o["id"],
                "qty": o.get("qty", 1),
                "unit_price": o.get("price", 0),
                "line_total": o.get("line_total", 0),
            }
            for o in selected_options
        ]
        fdb.save_offer_items(offer_id, items)

    return RedirectResponse(f"/offers/{offer_id}", 303)


@router.get("/{offer_id}/edit")
async def offer_edit(request: Request, offer_id: int):
    user = auth.require_user(request)
    offer = fdb.get_offer(offer_id)
    if not offer:
        return RedirectResponse("/offers", 303)
    items = fdb.get_offer_items(offer_id)
    _cust_dealer = None if user["role"] == "admin" else user["id"]
    customers = fdb.get_customers(dealer_id=_cust_dealer)
    cats = fdb.get_cats()
    models = fdb.get_models()
    options = fdb.get_options()
    cat_map = {c["id"]: c["name"] for c in cats}
    for m in models:
        m["category_name"] = cat_map.get(m.get("category_id"), "-")
        compat = []
        if m.get("compatible_options"):
            try:
                compat = json.loads(m["compatible_options"])
            except Exception:
                pass
        m["compatible_options_list"] = compat
        m["line_images_map"] = {img["line_count"]: img for img in fdb.get_model_line_images(m["id"])}
    delivery_terms = fdb.get_delivery_terms(active_only=True)
    return templates.TemplateResponse(request, "offer_wizard.html", {
        "user": user,
        "customers": customers,
        "categories": cats,
        "models": models,
        "options": options,
        "currencies": CURRENCIES,
        "delivery_terms": delivery_terms,
        "edit_offer": offer,
        "edit_items": items,
        "active_page": "offers",
    })


@router.post("/{offer_id}/update")
async def update_offer(request: Request,
                       offer_id: int,
                       customer_id: int = Form(0),
                       model_id: int = Form(...),
                       machine_count: int = Form(1),
                       currency: str = Form("USD"),
                       discount_pct: float = Form(0.0),
                       delivery_term_id: int = Form(0),
                       notes: str = Form(""),
                       validity_date: str = Form(""),
                       delivery_method: str = Form(""),
                       delivery_time: str = Form(""),
                       logistics: str = Form(""),
                       payment_notes: str = Form(""),
                       options_json: str = Form("[]")):
    auth.require_user(request)

    model = fdb.get_model(model_id)
    base_price = float(model["base_price"]) if model else 0.0

    selected_options = []
    try:
        selected_options = json.loads(options_json)
    except Exception:
        pass

    options_total = sum(float(o.get("line_total", 0)) for o in selected_options)
    subtotal = base_price * machine_count + options_total

    term = fdb.get_delivery_term(delivery_term_id) if delivery_term_id else None
    delivery_term_discount = float(term["discount_pct"]) if term else 0.0
    total_price = subtotal * (1 - delivery_term_discount / 100) * (1 - discount_pct / 100)

    fdb.upd_offer(offer_id,
        customer_id=customer_id or None,
        model_id=model_id,
        machine_count=machine_count,
        currency=currency,
        base_price=base_price,
        options_total=options_total,
        discount_pct=discount_pct,
        total_price=total_price,
        notes=notes,
        validity_date=validity_date,
        delivery_method=delivery_method,
        delivery_time=delivery_time,
        logistics=logistics,
        payment_notes=payment_notes,
        delivery_term_id=delivery_term_id or None,
        delivery_term_discount=delivery_term_discount,
    )

    fdb.save_offer_items(offer_id, [
        {"option_id": o["id"], "qty": o.get("qty", 1),
         "unit_price": o.get("price", 0), "line_total": o.get("line_total", 0)}
        for o in selected_options
    ])

    return RedirectResponse(f"/offers/{offer_id}", 303)


@router.get("/{offer_id}")
async def offer_detail(request: Request, offer_id: int):
    user = auth.require_user(request)
    offer = fdb.get_offer(offer_id)
    if not offer:
        return RedirectResponse("/offers", 303)
    items = fdb.get_offer_items(offer_id)
    customer = fdb.get_customer(offer["customer_id"]) if offer.get("customer_id") else {}
    model = fdb.get_model(offer["model_id"]) if offer.get("model_id") else {}
    opts = {o["id"]: o for o in fdb.get_options()}
    lang = user.get("lang", "tr")
    for item in items:
        opt = opts.get(item.get("option_id"), {})
        _resolve_opt_fields(item, opt, lang)
    display_image = _best_display_image(model, offer, items, opts)
    specs = _filter_specs(_parse_specs(model, lang), items, opts)
    delivery_term = fdb.get_delivery_term(offer["delivery_term_id"]) if offer.get("delivery_term_id") else None
    change_requests = fdb.get_change_requests(offer_id=offer_id)
    import db.users as udb
    manufacturers = udb.all_manufacturers() if user["role"] == "admin" else []
    default_mfr_id = (fdb.get_model(offer["model_id"]) or {}).get("manufacturer_id") or 0 if offer.get("model_id") else 0
    # Admin sees all statuses; dealers cannot select "Sipariş Verildi" directly
    if user["role"] == "admin":
        statuses = OFFER_STATUSES
    else:
        statuses = [s for s in OFFER_STATUSES if s != "Sipariş Verildi"]
    return templates.TemplateResponse(request, "offer_detail.html", {
        "user": user,
        "offer": offer,
        "items": items,
        "customer": customer,
        "model": model,
        "specs": specs,
        "delivery_term": delivery_term,
        "display_image": display_image,
        "statuses": statuses,
        "change_requests": change_requests,
        "manufacturers": manufacturers,
        "default_mfr_id": default_mfr_id,
        "active_page": "offers",
    })


@router.get("/{offer_id}/print")
async def offer_print(request: Request, offer_id: int):
    user = auth.require_user(request)
    offer = fdb.get_offer(offer_id)
    if not offer:
        return RedirectResponse("/offers", 303)
    items = fdb.get_offer_items(offer_id)
    customer = fdb.get_customer(offer["customer_id"]) if offer.get("customer_id") else {}
    model = fdb.get_model(offer["model_id"]) if offer.get("model_id") else {}
    opts = {o["id"]: o for o in fdb.get_options()}
    lang = user.get("lang", "tr")
    for item in items:
        opt = opts.get(item.get("option_id"), {})
        _resolve_opt_fields(item, opt, lang)
    display_image = _best_display_image(model, offer, items, opts)

    specs = _filter_specs(_parse_specs(model, lang), items, opts)

    return templates.TemplateResponse(request, "offer_print.html", {
        "user": user,
        "offer": offer,
        "customer": customer or {},
        "model": model or {},
        "items": items,
        "specs": specs,
        "display_image": display_image,
        "lang": lang,
    })


@router.get("/{offer_id}/pdf-view")
async def offer_pdf_view(request: Request, offer_id: int):
    user = auth.require_user(request)
    offer = fdb.get_offer(offer_id)
    if not offer:
        return RedirectResponse("/offers", 303)
    customer = fdb.get_customer(offer["customer_id"]) if offer.get("customer_id") else {}
    return templates.TemplateResponse(request, "offer_pdf_view.html", {
        "user": user,
        "offer": offer,
        "customer": customer or {},
    })


@router.get("/{offer_id}/pdf")
async def offer_pdf(request: Request, offer_id: int, dl: int = 0):
    user = auth.require_user(request)
    offer = fdb.get_offer(offer_id)
    if not offer:
        return RedirectResponse("/offers", 303)
    items = fdb.get_offer_items(offer_id)
    customer = fdb.get_customer(offer["customer_id"]) if offer.get("customer_id") else {}
    model = fdb.get_model(offer["model_id"]) if offer.get("model_id") else {}
    opts = {o["id"]: o for o in fdb.get_options()}
    lang = user.get("lang", "tr")
    for item in items:
        opt = opts.get(item.get("option_id"), {})
        _resolve_opt_fields(item, opt, lang)
    display_image = _best_display_image(model, offer, items, opts)

    specs = _filter_specs(_parse_specs(model, lang), items, opts)

    company = fdb.get_company() or {}
    delivery_term = fdb.get_delivery_term(offer["delivery_term_id"]) if offer.get("delivery_term_id") else None
    html_str = templates.get_template("offer_pdf.html").render(
        offer=offer,
        customer=customer or {},
        model=model or {},
        items=items,
        specs=specs,
        display_image=display_image,
        lang=lang,
        admin_logo=company.get("logo_path", "") or "",
        admin_company=company.get("company_name", "") or "",
        delivery_term=delivery_term,
    )
    from weasyprint import HTML as WH
    pdf_bytes = WH(string=html_str, base_url="http://127.0.0.1:8501/").write_pdf()
    fname = f"Teklif_{offer['offer_no']}.pdf"
    disposition = "attachment" if dl else "inline"
    return Response(pdf_bytes, media_type="application/pdf",
                    headers={"Content-Disposition": f'{disposition}; filename="{fname}"'})


@router.get("/{offer_id}/catalog-pdf")
async def offer_catalog_pdf(request: Request, offer_id: int):
    """Generate an individual catalog PDF for the model in this offer, using only the selected options."""
    import asyncio
    import unicodedata
    from catalog_ai import generate_catalog_content

    user = auth.require_user(request)
    offer = fdb.get_offer(offer_id)
    if not offer:
        return RedirectResponse("/offers", 303)

    lang = user.get("lang") or "tr"

    model_id = offer.get("model_id")
    if not model_id:
        return Response("Bu teklifte makine tanımlı değil.", status_code=400, media_type="text/plain")

    m = fdb.get_model(model_id)
    if not m:
        return Response("Model bulunamadı.", status_code=404, media_type="text/plain")

    # Parse specs (language-specific)
    specs_key = "specs" if lang == "tr" else f"specs_{lang}"
    raw = m.get(specs_key) or m.get("specs") or "[]"
    try:
        specs = json.loads(raw) if isinstance(raw, str) else raw
    except Exception:
        specs = []

    # Only include options selected in this offer
    items = fdb.get_offer_items(offer_id)
    option_ids = {item["option_id"] for item in items if item.get("option_id")}
    all_opts = {o["id"]: o for o in fdb.get_options()}
    options = [all_opts[oid] for oid in option_ids if oid in all_opts]

    # Category / company
    cats = fdb.get_cats()
    cat = {c["id"]: c for c in cats}.get(m.get("category_id"), {})
    category_name = cat.get(f"name_{lang}") or cat.get("name") or ""
    company = fdb.get_company()
    model_name = m.get(f"name_{lang}") or m.get("name") or ""

    # AI content (blocking — run in thread)
    ai = await asyncio.to_thread(generate_catalog_content, m, lang, specs, options)

    _L = {
        "tr": {
            "overview": "Ürün Genel Bakış", "highlights": "Temel Özellikler",
            "specs": "Teknik Özellikler", "spec_feature": "Özellik", "spec_detail": "Detay",
            "options": "Opsiyonlar & Aksesuarlar", "phone": "Telefon", "email": "E-posta",
            "web": "Web", "product_catalog": "Ürün Kataloğu", "contact_us": "İletişim",
            "address": "Adres", "option_benefits": "Seçili Opsiyonların Sağladığı Faydalar",
        },
        "en": {
            "overview": "Product Overview", "highlights": "Key Features",
            "specs": "Technical Specifications", "spec_feature": "Feature", "spec_detail": "Detail",
            "options": "Options & Accessories", "phone": "Phone", "email": "Email",
            "web": "Website", "product_catalog": "Product Catalog", "contact_us": "Contact Us",
            "address": "Address", "option_benefits": "Benefits of Selected Options",
        },
        "zh": {
            "overview": "产品概览", "highlights": "核心特点",
            "specs": "技术规格", "spec_feature": "特性", "spec_detail": "详情",
            "options": "选项与配件", "phone": "电话", "email": "邮箱",
            "web": "网站", "product_catalog": "产品目录", "contact_us": "联系我们",
            "address": "地址", "option_benefits": "所选选项的优势",
        },
    }
    lbl = _L.get(lang, _L["tr"])

    base_url = str(request.base_url).rstrip("/")
    date_str = datetime.date.today().strftime("%Y-%m-%d")

    html_str = templates.get_template("catalog_pdf.html").render({
        "model": m,
        "model_name": model_name,
        "specs": specs,
        "options": options,
        "category_name": category_name,
        "company": company,
        "ai": ai,
        "lang": lang,
        "base_url": base_url,
        "date_str": date_str,
        "label_overview":        lbl["overview"],
        "label_highlights":      lbl["highlights"],
        "label_specs":           lbl["specs"],
        "label_spec_feature":    lbl["spec_feature"],
        "label_spec_detail":     lbl["spec_detail"],
        "label_options":         lbl["options"],
        "label_phone":           lbl["phone"],
        "label_email":           lbl["email"],
        "label_web":             lbl["web"],
        "label_product_catalog": lbl["product_catalog"],
        "label_contact_us":      lbl["contact_us"],
        "label_address":         lbl["address"],
        "label_option_benefits": lbl["option_benefits"],
    })

    def _render():
        from weasyprint import HTML
        return HTML(string=html_str, base_url=base_url).write_pdf()

    try:
        pdf = await asyncio.to_thread(_render)
    except Exception as e:
        return Response(f"PDF oluşturulamadı: {e}", status_code=500, media_type="text/plain")

    safe = unicodedata.normalize("NFKD", model_name)
    safe = "".join(c for c in safe if ord(c) < 128).replace(" ", "_")[:30] or "katalog"
    fname = f"Katalog_{safe}_{lang}.pdf"
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{fname}"'})


@router.post("/{offer_id}/cancel-offer")
async def cancel_offer(request: Request,
                       offer_id: int,
                       cancel_reason: str = Form("")):
    user = auth.require_user(request)
    offer = fdb.get_offer(offer_id)
    if not offer:
        return RedirectResponse("/offers", 303)
    if user["role"] != "admin" and offer.get("dealer_id") != user["id"]:
        return RedirectResponse(f"/offers/{offer_id}", 303)
    fdb.cancel_offer(offer_id, cancel_reason)
    return RedirectResponse(f"/offers/{offer_id}", 303)


@router.post("/{offer_id}/dealer-approve")
async def dealer_approve(request: Request,
                         offer_id: int,
                         contract_notes: str = Form(""),
                         contract_photo: Optional[UploadFile] = File(None)):
    user = auth.require_user(request)
    offer = fdb.get_offer(offer_id)
    if not offer:
        return RedirectResponse("/offers", 303)
    if user["role"] != "admin" and offer.get("dealer_id") != user["id"]:
        return RedirectResponse(f"/offers/{offer_id}", 303)

    photo_path = ""
    if contract_photo and contract_photo.filename:
        ext = os.path.splitext(contract_photo.filename)[1].lower() or ".jpg"
        fname = f"contract_{offer_id}_{uuid.uuid4().hex[:8]}{ext}"
        content = await contract_photo.read()
        with open(os.path.join(CONTRACTS_DIR, fname), "wb") as f:
            f.write(content)
        photo_path = f"contracts/{fname}"

    fdb.dealer_approve_offer(offer_id, contract_notes, photo_path)

    def _send():
        try:
            from email_utils import send_admin_notification
            send_admin_notification("Bayi Siparişi Onayladı", {
                "Teklif No": f"#{offer_id}",
                "Bayi": user.get("company_name", "-"),
                "Not": contract_notes or "-",
            })
        except Exception:
            pass
    threading.Thread(target=_send, daemon=True).start()

    return RedirectResponse(f"/offers/{offer_id}", 303)


@router.post("/{offer_id}/change-request")
async def send_change_request(request: Request,
                              offer_id: int,
                              description: str = Form(...)):
    user = auth.require_user(request)
    offer = fdb.get_offer(offer_id)
    if not offer:
        return RedirectResponse("/offers", 303)
    fdb.save_change_request(offer_id, user["id"], description)

    def _send():
        try:
            from email_utils import send_admin_notification
            send_admin_notification("Değişiklik Talebi", {
                "Teklif No": f"#{offer_id}",
                "Bayi": user.get("company_name", "-"),
                "Talep": description,
            })
        except Exception:
            pass
    threading.Thread(target=_send, daemon=True).start()

    return RedirectResponse(f"/offers/{offer_id}", 303)


@router.post("/{offer_id}/change-request/resolve")
async def resolve_change_request(request: Request,
                                  offer_id: int,
                                  req_id: int = Form(...),
                                  action: str = Form(...),
                                  admin_notes: str = Form("")):
    auth.require_admin(request)
    fdb.resolve_change_request(req_id, action, admin_notes)
    return RedirectResponse(f"/offers/{offer_id}", 303)


@router.post("/{offer_id}/status")
async def update_status(request: Request,
                        offer_id: int,
                        status: str = Form(...)):
    user = auth.require_user(request)
    fdb.upd_offer_status(offer_id, status)
    if status == "Sipariş Verildi":
        import threading
        offer = fdb.get_offer(offer_id)
        def _send():
            try:
                from email_utils import send_admin_notification
                send_admin_notification("Yeni Sipariş Verildi", {
                    "Teklif No": f"#{offer_id}",
                    "Bayi": user.get("company_name", "-"),
                    "Müşteri": (offer or {}).get("customer_name", "-"),
                    "Model": (offer or {}).get("model_name", "-"),
                })
            except Exception:
                pass
        threading.Thread(target=_send, daemon=True).start()
    return RedirectResponse(f"/offers/{offer_id}", 303)


@router.post("/delete")
async def delete_offer(request: Request, id: int = Form(...)):
    auth.require_user(request)
    fdb.del_offer(id)
    return RedirectResponse("/offers", 303)
