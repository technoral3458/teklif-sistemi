import json
from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
import db.factory as fdb
import auth
from tmpl import templates

router = APIRouter(prefix="/admin/teklif-talepleri")

STATUSES = ["Yeni", "İncelendi", "Teklif Hazırlandı", "Reddedildi"]


@router.get("")
async def list_requests(request: Request, status: str = ""):
    user = auth.require_admin(request)
    reqs = fdb.get_quote_requests(status or None)
    for r in reqs:
        try:
            r["options_list"] = json.loads(r.get("options_json") or "[]")
        except Exception:
            r["options_list"] = []
    return templates.TemplateResponse(request, "quote_requests.html", {
        "user": user,
        "requests": reqs,
        "statuses": STATUSES,
        "active_status": status,
        "active_page": "quote_requests",
    })


@router.get("/{rid}")
async def request_detail(request: Request, rid: int):
    user = auth.require_admin(request)
    req = fdb.get_quote_request(rid)
    if not req:
        return RedirectResponse("/admin/teklif-talepleri", 303)
    try:
        req["options_list"] = json.loads(req.get("options_json") or "[]")
    except Exception:
        req["options_list"] = []
    model = fdb.get_model(req["model_id"]) if req.get("model_id") else {}
    # Auto-mark as seen
    if req["status"] == "Yeni":
        fdb.upd_quote_request_status(rid, "İncelendi")
        req["status"] = "İncelendi"
    return templates.TemplateResponse(request, "quote_request_detail.html", {
        "user": user,
        "req": req,
        "model": model or {},
        "statuses": STATUSES,
        "active_page": "quote_requests",
    })


@router.post("/{rid}/status")
async def update_status(request: Request, rid: int, status: str = Form(...)):
    auth.require_admin(request)
    fdb.upd_quote_request_status(rid, status)
    return RedirectResponse(f"/admin/teklif-talepleri/{rid}", 303)


@router.post("/{rid}/delete")
async def delete_request(request: Request, rid: int):
    auth.require_admin(request)
    fdb.del_quote_request(rid)
    return RedirectResponse("/admin/teklif-talepleri", 303)


@router.post("/{rid}/convert")
async def convert_to_offer(request: Request, rid: int):
    """Convert a quote request into a draft offer pre-filled in the wizard."""
    auth.require_admin(request)
    req = fdb.get_quote_request(rid)
    if not req:
        return RedirectResponse("/admin/teklif-talepleri", 303)
    fdb.upd_quote_request_status(rid, "Teklif Hazırlandı")
    # Redirect to offer wizard with pre-fill params
    params = f"?prefill_model={req.get('model_id') or ''}&prefill_company={req.get('company_name','')}&prefill_name={req.get('customer_name','')}&prefill_email={req.get('email','')}&prefill_phone={req.get('phone','')}&prefill_note={req.get('note','')}&prefill_count={req.get('machine_count',1)}"
    return RedirectResponse(f"/offers/new{params}", 303)
