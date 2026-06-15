from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse

import db.factory as fdb
import db.users as udb
import auth

router = APIRouter(prefix="/admin/requests")
from tmpl import templates


@router.get("")
async def requests_list(request: Request):
    user = auth.require_admin(request)
    reqs = fdb.get_deletion_requests()
    user_map = {u["id"]: u for u in udb.all_users()}
    for r in reqs:
        r["requester"] = user_map.get(r["requested_by"], {})
    pending_count = sum(1 for r in reqs if r["status"] == "pending")
    return templates.TemplateResponse(request, "admin_requests.html", {
        "user": user,
        "requests": reqs,
        "pending_count": pending_count,
        "active_page": "admin_requests",
    })


@router.post("/approve")
async def approve_request(request: Request, req_id: int = Form(...)):
    auth.require_admin(request)
    reqs = fdb.get_deletion_requests()
    req = next((r for r in reqs if r["id"] == req_id), None)
    if not req or req["status"] != "pending":
        return RedirectResponse("/admin/requests?msg=Talep+bulunamadı&msg_type=error", 303)
    if req["item_type"] == "model":
        fdb.del_model(req["item_id"])
    elif req["item_type"] == "option":
        fdb.del_option(req["item_id"])
    fdb.resolve_deletion_request(req_id, "approved")
    return RedirectResponse("/admin/requests?msg=Silme+onaylandı&msg_type=success", 303)


@router.post("/reject")
async def reject_request(request: Request, req_id: int = Form(...)):
    auth.require_admin(request)
    fdb.resolve_deletion_request(req_id, "rejected")
    return RedirectResponse("/admin/requests?msg=Talep+reddedildi&msg_type=info", 303)
