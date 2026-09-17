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
    _ulang = user.get("lang") or "tr"
    cat_map = {c["id"]: (c.get(f"name_{_ulang}") or c["name"]) if _ulang != "tr" else c["name"] for c in cats}
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
                       options_json: str = Form("[]"),
                       final_price: str = Form("")):
    user = auth.require_user(request)
    final_price_val = float(final_price.strip()) if final_price.strip() else 0.0

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
    saved_model_name = (model.get("name") or "") if model else ""

    selected_options = []
    try:
        selected_options = json.loads(options_json)
    except Exception:
        pass

    options_total = sum(float(o.get("line_total", 0)) for o in selected_options)
    subtotal = base_price * machine_count + options_total

    term = fdb.get_delivery_term(delivery_term_id) if delivery_term_id else None
    delivery_term_discount = float(term["discount_pct"]) if term else 0.0
    calculated_price = subtotal * (1 - delivery_term_discount / 100) * (1 - discount_pct / 100)
    total_price = final_price_val if final_price_val > 0 else calculated_price

    offer_no = f"TKL-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"

    offer_id = fdb.create_offer(
        offer_no=offer_no,
        customer_id=customer_id,
        model_id=model_id,
        model_name=saved_model_name,
        machine_count=machine_count,
        currency=currency,
        base_price=base_price,
        options_total=options_total,
        discount_pct=discount_pct,
        total_price=total_price,
        final_price=final_price_val,
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
    _ulang = user.get("lang") or "tr"
    cat_map = {c["id"]: (c.get(f"name_{_ulang}") or c["name"]) if _ulang != "tr" else c["name"] for c in cats}
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
                       options_json: str = Form("[]"),
                       final_price: str = Form("")):
    auth.require_user(request)
    final_price_val = float(final_price.strip()) if final_price.strip() else 0.0

    model = fdb.get_model(model_id)
    base_price = float(model["base_price"]) if model else 0.0
    saved_model_name = (model.get("name") or "") if model else ""

    selected_options = []
    try:
        selected_options = json.loads(options_json)
    except Exception:
        pass

    options_total = sum(float(o.get("line_total", 0)) for o in selected_options)
    subtotal = base_price * machine_count + options_total

    term = fdb.get_delivery_term(delivery_term_id) if delivery_term_id else None
    delivery_term_discount = float(term["discount_pct"]) if term else 0.0
    calculated_price = subtotal * (1 - delivery_term_discount / 100) * (1 - discount_pct / 100)
    total_price = final_price_val if final_price_val > 0 else calculated_price

    fdb.upd_offer(offer_id,
        customer_id=customer_id or None,
        model_id=model_id,
        model_name=saved_model_name,
        machine_count=machine_count,
        currency=currency,
        base_price=base_price,
        options_total=options_total,
        discount_pct=discount_pct,
        total_price=total_price,
        final_price=final_price_val,
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


@router.get("/{offer_id}/social-card")
async def social_card(request: Request, offer_id: int):
    import io, textwrap, re
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
    from fastapi.responses import Response as FResponse

    user = auth.require_user(request)
    offer = fdb.get_offer(offer_id)
    if not offer:
        return RedirectResponse("/offers", 303)

    model   = fdb.get_model(offer["model_id"]) if offer.get("model_id") else {}
    items   = fdb.get_offer_items(offer_id)
    opts    = {o["id"]: o for o in fdb.get_options()}
    specs   = _filter_specs(_parse_specs(model or {}, "tr"), items, opts)
    display = _best_display_image(model or {}, offer, items, opts)
    company = fdb.get_company() or {}

    model_name = (model or {}).get("name", offer.get("model_name", "")) or ""

    # ── AI: select top specs & headline ────────────────────────────────────────
    from config import ANTHROPIC_API_KEY
    import httpx as _hx

    headline  = model_name
    key_specs = []

    if specs:
        for s in specs[:5]:
            t = (s.get("title") or "").strip()
            d = (s.get("desc") or "").strip()
            if t:
                key_specs.append(f"{t}: {d}" if d else t)

    if ANTHROPIC_API_KEY and specs:
        spec_block = "\n".join(f"- {s.get('title','')}: {s.get('desc','')}" for s in specs[:15])
        try:
            async with _hx.AsyncClient(timeout=12) as cli:
                r = await cli.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={"x-api-key": ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01",
                             "content-type": "application/json"},
                    json={
                        "model": "claude-haiku-4-5-20251001",
                        "max_tokens": 256,
                        "messages": [{"role": "user", "content":
                            f"Makina: {model_name}\nÖzellikler:\n{spec_block}\n\n"
                            "Bu makina için Instagram pazarlama görseli yapıyoruz. JSON döndür:\n"
                            '{{"headline":"max 7 kelime etkileyici Türkçe başlık",'
                            '"specs":["4 adet kısa öne çıkan özellik, değer dahil, örn: 180 Parça/Saat"]}}'
                        }],
                    }
                )
            if r.status_code == 200:
                txt = r.json()["content"][0]["text"]
                m = re.search(r'\{.*\}', txt, re.DOTALL)
                if m:
                    d = json.loads(m.group())
                    headline  = d.get("headline", model_name) or model_name
                    ai_specs  = d.get("specs") or []
                    if ai_specs:
                        key_specs = [str(s) for s in ai_specs[:4]]
        except Exception:
            pass

    if not key_specs:
        key_specs = [f"{s.get('title','')}: {s.get('desc','')}" for s in specs[:4] if s.get("title")]

    # ── Pillow: build 1080×1080 image ─────────────────────────────────────────
    W = H = 1080
    DARK   = (10, 22, 40)
    ACCENT = (56, 182, 255)
    GREEN  = (52, 211, 153)
    WHITE  = (255, 255, 255)
    MUTED  = (160, 185, 215)

    canvas = Image.new("RGB", (W, H), DARK)
    draw   = ImageDraw.Draw(canvas)

    # Background: blurred machine image
    if display:
        img_path = os.path.join(BASE_DIR, "static", display)
        if os.path.exists(img_path):
            try:
                bg = Image.open(img_path).convert("RGB")
                bg = bg.resize((W, H), Image.LANCZOS)
                bg = bg.filter(ImageFilter.GaussianBlur(18))
                # Darken
                overlay = Image.new("RGB", (W, H), DARK)
                canvas = Image.blend(bg, overlay, alpha=0.70)
                draw   = ImageDraw.Draw(canvas)
            except Exception:
                pass

    # Left gradient panel (makes text readable)
    for x in range(600):
        a = int(220 * (1 - x / 600) ** 0.5)
        draw.line([(x, 0), (x, H)], fill=(*DARK, a))

    # Right: clean machine image
    if display:
        img_path = os.path.join(BASE_DIR, "static", display)
        if os.path.exists(img_path):
            try:
                mach = Image.open(img_path).convert("RGBA")
                max_w, max_h = 560, 660
                mach.thumbnail((max_w, max_h), Image.LANCZOS)
                x_pos = W - mach.width - 20
                y_pos = (H - mach.height) // 2
                canvas.paste(mach, (x_pos, y_pos), mach)
            except Exception:
                pass

    # Fonts
    FONT_DIR = "/usr/share/fonts/truetype/liberation"
    def _f(size, bold=True):
        try:
            fname = "LiberationSans-Bold.ttf" if bold else "LiberationSans-Regular.ttf"
            return ImageFont.truetype(os.path.join(FONT_DIR, fname), size)
        except Exception:
            return ImageFont.load_default()

    # Company logo (top-left)
    logo_y = 54
    logo_bottom = logo_y
    logo_path = company.get("logo_path", "")
    if logo_path:
        lp = os.path.join(BASE_DIR, "static", logo_path)
        if os.path.exists(lp):
            try:
                logo = Image.open(lp).convert("RGBA")
                logo.thumbnail((220, 72), Image.LANCZOS)
                canvas.paste(logo, (54, logo_y), logo)
                logo_bottom = logo_y + logo.height + 8
            except Exception:
                pass
    if logo_bottom == logo_y:
        company_name_top = company.get("company_name", "")
        if company_name_top:
            draw.text((54, logo_y), company_name_top, font=_f(28), fill=ACCENT)
            logo_bottom = logo_y + 40

    # Accent top line
    draw.rectangle([(54, logo_bottom + 12), (320, logo_bottom + 16)], fill=ACCENT)

    # Headline
    hl_y = logo_bottom + 36
    hl_font = _f(52)
    # Wrap headline to fit left panel
    words = headline.split()
    lines, line = [], ""
    for w in words:
        test = (line + " " + w).strip()
        bbox = draw.textbbox((0, 0), test, font=hl_font)
        if bbox[2] > 520:
            if line:
                lines.append(line)
            line = w
        else:
            line = test
    if line:
        lines.append(line)
    for ln in lines[:3]:
        draw.text((54, hl_y), ln, font=hl_font, fill=WHITE)
        hl_y += 62

    # Model name
    hl_y += 8
    draw.text((54, hl_y), model_name, font=_f(30, bold=False), fill=ACCENT)
    hl_y += 50

    # Separator
    draw.rectangle([(54, hl_y), (260, hl_y + 2)], fill=(*GREEN, 180))
    hl_y += 20

    # Key specs
    spec_font  = _f(28)
    label_font = _f(20, bold=False)
    dot_color  = GREEN
    for spec_str in key_specs[:4]:
        if ":" in spec_str:
            label, val = spec_str.split(":", 1)
            draw.text((54, hl_y), "▸ ", font=spec_font, fill=dot_color)
            draw.text((84, hl_y), val.strip(), font=spec_font, fill=WHITE)
            draw.text((84, hl_y + 32), label.strip(), font=label_font, fill=MUTED)
            hl_y += 78
        else:
            draw.text((54, hl_y), f"▸  {spec_str}", font=spec_font, fill=WHITE)
            hl_y += 54

    # Bottom bar
    draw.rectangle([(0, H - 90), (W, H)], fill=(6, 14, 26))
    draw.rectangle([(0, H - 90), (W, H - 87)], fill=ACCENT)
    company_name = company.get("company_name", "")
    website      = company.get("website", "") or ""
    bottom_text  = company_name
    if website:
        bottom_text += f"  ·  {website}"
    if bottom_text:
        draw.text((54, H - 64), bottom_text, font=_f(26, bold=False), fill=WHITE)

    # Save
    buf = io.BytesIO()
    canvas.save(buf, format="PNG", optimize=True)
    buf.seek(0)
    slug = re.sub(r"[^a-z0-9-]", "-", model_name.lower())[:30].strip("-") or "kart"
    return FResponse(
        content=buf.read(),
        media_type="image/png",
        headers={"Content-Disposition": f'attachment; filename="sosyal-{slug}-{offer_id}.png"'},
    )


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

    # Best display image (variation image > line image > model image)
    opts_map = {o["id"]: o for o in fdb.get_options()}
    display_image = _best_display_image(m, offer, items, opts_map)

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
        "display_image": display_image,
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
