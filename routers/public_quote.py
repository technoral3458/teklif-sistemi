import json
from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse, JSONResponse
import db.factory as fdb
from tmpl import templates

router = APIRouter(prefix="/teklif-al")


@router.get("")
async def quote_page(request: Request):
    models = [m for m in fdb.get_models() if m.get("is_active", 1) != 0]
    categories = fdb.get_cats()
    company = fdb.get_company() or {}
    for m in models:
        m["line_images_map"] = {img["line_count"]: img for img in fdb.get_model_line_images(m["id"])}
    return templates.TemplateResponse(request, "public_quote.html", {
        "user": None,
        "models": models,
        "categories": categories,
        "company": company,
        "active_page": "public_quote",
    })


@router.post("/submit")
async def quote_submit(
    request: Request,
    model_id: int = Form(0),
    model_name: str = Form(""),
    machine_count: int = Form(1),
    options_json: str = Form("[]"),
    customer_name: str = Form(""),
    company_name: str = Form(""),
    email: str = Form(""),
    phone: str = Form(""),
    note: str = Form(""),
):
    # Basic validation
    if not customer_name.strip() or not email.strip():
        return RedirectResponse("/teklif-al?err=missing_fields", 303)

    rid, ref = fdb.add_quote_request(
        model_id=model_id or None,
        model_name=model_name.strip(),
        machine_count=max(1, machine_count),
        options_json=options_json,
        customer_name=customer_name.strip(),
        company_name=company_name.strip(),
        email=email.strip().lower(),
        phone=phone.strip(),
        note=note.strip(),
    )

    # Email notification to admin (best-effort)
    try:
        from email_utils import send_admin_notification
        send_admin_notification("Yeni Teklif Talebi", {
            "Referans": ref,
            "Makine": model_name,
            "Adet": machine_count,
            "Müşteri": customer_name,
            "Firma": company_name,
            "E-posta": email,
            "Telefon": phone,
        })
    except Exception:
        pass

    return RedirectResponse(f"/teklif-al/tesekkurler?ref={ref}", 303)


@router.get("/options")
async def get_options(request: Request, model_id: int = 0):
    """Return compatible options for a model (no prices) as JSON."""
    opts = fdb.get_options()
    model = fdb.get_model(model_id) if model_id else None
    compat_ids = set()
    if model:
        try:
            compat_ids = set(json.loads(model.get("compatible_options_list") or "[]"))
        except Exception:
            pass

    result = []
    for o in opts:
        if not o.get("is_active", 1):
            continue
        if compat_ids and o["id"] not in compat_ids:
            continue
        result.append({
            "id": o["id"],
            "name": o.get("name") or "",
            "description": o.get("description") or "",
            "group_name": o.get("group_name") or "",
            "conflict_group": o.get("conflict_group") or "",
            "image_path": o.get("image_path") or "",
            "scope": o.get("scope") or "GLOBAL",
        })
    return JSONResponse(result)


@router.get("/tesekkurler")
async def quote_thanks(request: Request, ref: str = ""):
    company = fdb.get_company() or {}
    return templates.TemplateResponse(request, "public_quote_thanks.html", {
        "user": None,
        "ref": ref,
        "company": company,
        "active_page": "public_quote",
    })
