import json
import datetime

from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse, Response

import db.factory as fdb
import auth
from config import OFFER_STATUSES, CURRENCIES, BASE_DIR

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


@router.get("")
async def offers_list(request: Request, status: str = "", q: str = ""):
    user = auth.require_user(request)
    offers = fdb.get_offers(status=status or None)
    customers = {c["id"]: c for c in fdb.get_customers()}
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
    customers = fdb.get_customers()
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
    return templates.TemplateResponse(request, "offer_wizard.html", {
        "user": user,
        "customers": customers,
        "categories": cats,
        "models": models,
        "options": options,
        "currencies": CURRENCIES,
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
    total_price = subtotal * (1 - discount_pct / 100)

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
    customers = fdb.get_customers()
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
    return templates.TemplateResponse(request, "offer_wizard.html", {
        "user": user,
        "customers": customers,
        "categories": cats,
        "models": models,
        "options": options,
        "currencies": CURRENCIES,
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
    total_price = subtotal * (1 - discount_pct / 100)

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
    best_prio, display_image = -1, (model.get("image_path", "") if model else "")
    lang = user.get("lang", "tr")
    for item in items:
        opt = opts.get(item.get("option_id"), {})
        item["option_name"] = (opt.get(f"name_{lang}") or opt.get("name", "-")) if lang != "tr" else opt.get("name", "-")
        item["image_path"]  = opt.get("image_path", "") or ""
        item["description"] = opt.get("description", "") or ""
        item["video_url"]   = opt.get("video_url", "") or ""
        var_img = opt.get("variation_image_path", "")
        prio = opt.get("image_priority") or 0
        if var_img and prio > best_prio:
            display_image, best_prio = var_img, prio
    return templates.TemplateResponse(request, "offer_detail.html", {
        "user": user,
        "offer": offer,
        "items": items,
        "customer": customer,
        "model": model,
        "display_image": display_image,
        "statuses": OFFER_STATUSES,
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

    best_prio, display_image = -1, (model.get("image_path", "") if model else "")
    lang = user.get("lang", "tr")
    for item in items:
        opt = opts.get(item.get("option_id"), {})
        item["option_name"] = (opt.get(f"name_{lang}") or opt.get("name", "-")) if lang != "tr" else opt.get("name", "-")
        item["description"] = opt.get("description", "") or ""
        item["image_path"] = opt.get("image_path", "") or ""
        item["video_url"]  = opt.get("video_url", "") or ""
        var_img = opt.get("variation_image_path", "")
        prio = opt.get("image_priority") or 0
        if var_img and prio > best_prio:
            display_image, best_prio = var_img, prio

    specs = []
    raw = (model.get("specs", "") or "") if model else ""
    if raw.strip().startswith("["):
        try:
            specs = json.loads(raw)
        except Exception:
            pass
    elif raw.strip().startswith("{"):
        try:
            obj = json.loads(raw)
            specs = [{"title": k, "desc": str(v), "img": ""} for k, v in obj.items()]
        except Exception:
            pass

    specs = _filter_specs(specs, items, opts)

    return templates.TemplateResponse(request, "offer_print.html", {
        "offer": offer,
        "customer": customer or {},
        "model": model or {},
        "items": items,
        "specs": specs,
        "display_image": display_image,
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

    best_prio, display_image = -1, (model.get("image_path", "") if model else "")
    lang = user.get("lang", "tr")
    for item in items:
        opt = opts.get(item.get("option_id"), {})
        item["option_name"] = (opt.get(f"name_{lang}") or opt.get("name", "-")) if lang != "tr" else opt.get("name", "-")
        item["description"] = opt.get("description", "") or ""
        item["image_path"] = opt.get("image_path", "") or ""
        item["video_url"]  = opt.get("video_url", "") or ""
        var_img = opt.get("variation_image_path", "")
        prio = opt.get("image_priority") or 0
        if var_img and prio > best_prio:
            display_image, best_prio = var_img, prio

    specs = []
    raw = (model.get("specs", "") or "") if model else ""
    if raw.strip().startswith("["):
        try:
            specs = json.loads(raw)
        except Exception:
            pass
    elif raw.strip().startswith("{"):
        try:
            obj = json.loads(raw)
            specs = [{"title": k, "desc": str(v), "img": ""} for k, v in obj.items()]
        except Exception:
            pass

    specs = _filter_specs(specs, items, opts)

    company = fdb.get_company() or {}
    html_str = templates.get_template("offer_pdf.html").render(
        offer=offer,
        customer=customer or {},
        model=model or {},
        items=items,
        specs=specs,
        display_image=display_image,
        admin_logo=company.get("logo_path", "") or "",
        admin_company=company.get("company_name", "") or "",
    )
    from weasyprint import HTML as WH
    pdf_bytes = WH(string=html_str, base_url="http://127.0.0.1:8501/").write_pdf()
    fname = f"Teklif_{offer['offer_no']}.pdf"
    disposition = "attachment" if dl else "inline"
    return Response(pdf_bytes, media_type="application/pdf",
                    headers={"Content-Disposition": f'{disposition}; filename="{fname}"'})


@router.post("/{offer_id}/status")
async def update_status(request: Request,
                        offer_id: int,
                        status: str = Form(...)):
    auth.require_user(request)
    fdb.upd_offer_status(offer_id, status)
    return RedirectResponse(f"/offers/{offer_id}", 303)


@router.post("/delete")
async def delete_offer(request: Request, id: int = Form(...)):
    auth.require_user(request)
    fdb.del_offer(id)
    return RedirectResponse("/offers", 303)
