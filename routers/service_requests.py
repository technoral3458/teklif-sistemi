"""Servis (arıza) talepleri — giriş yapmadan oluşturulur, panelde takip edilir."""

import io
import json
import os
import re

from fastapi import APIRouter, Request, Form, UploadFile, File
from fastapi.responses import RedirectResponse, Response
from starlette.concurrency import run_in_threadpool

import auth
import db.factory as fdb
from config import DATA_DIR
from tmpl import templates

router = APIRouter()

SERVICE_DIR = os.path.join(DATA_DIR, "service")
os.makedirs(SERVICE_DIR, exist_ok=True)

MAX_IMAGES = 5
MAX_IMAGE_MB = 12
MAX_SIDE = 2000          # telefon fotoğrafları diski şişirmesin
IMAGE_EXTS = {"png", "jpg", "jpeg", "webp", "bmp", "gif"}


def _digits(s):
    return re.sub(r"\D", "", s or "")


def _images(req):
    try:
        v = json.loads(req.get("images_json") or "[]")
        return v if isinstance(v, list) else []
    except Exception:
        return []


def _save_image(data: bytes, rid_tag: str, idx: int):
    """Resmi doğrula, gerekiyorsa küçült, JPEG olarak kaydet. Dosya adını döndürür."""
    from PIL import Image
    im = Image.open(io.BytesIO(data))
    im.load()
    if im.mode in ("RGBA", "LA", "P"):
        im = im.convert("RGBA")
        bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
        im = Image.alpha_composite(bg, im)
    im = im.convert("RGB")
    if max(im.size) > MAX_SIDE:
        r = MAX_SIDE / max(im.size)
        im = im.resize((max(1, int(im.width * r)), max(1, int(im.height * r))),
                       Image.LANCZOS)
    name = f"{rid_tag}_{idx}.jpg"
    im.save(os.path.join(SERVICE_DIR, name), "JPEG", quality=82, optimize=True)
    return name


# ══════════════════════════════════════════════════════════════════════════
#  Müşteri tarafı — giriş gerekmez
# ══════════════════════════════════════════════════════════════════════════

@router.get("/servis-talebi")
async def service_form(request: Request, err: str = ""):
    company = fdb.get_company() or {}
    models = [m["name"] for m in fdb.get_models() if m.get("is_active", 1) != 0]
    return templates.TemplateResponse(request, "service_request.html", {
        "user": None,
        "company": company,
        "models": sorted(set(models)),
        "err": err,
        "max_images": MAX_IMAGES,
        "max_mb": MAX_IMAGE_MB,
    })


@router.post("/servis-talebi/gonder")
async def service_submit(
    request: Request,
    serial_no: str = Form(""),
    model_name: str = Form(""),
    fault_desc: str = Form(""),
    first_name: str = Form(""),
    last_name: str = Form(""),
    phone: str = Form(""),
    email: str = Form(""),
    company_name: str = Form(""),
    photos: list[UploadFile] = File(default=[]),
):
    first_name = (first_name or "").strip()
    last_name = (last_name or "").strip()
    phone = (phone or "").strip()
    serial_no = (serial_no or "").strip()
    model_name = (model_name or "").strip()
    fault_desc = (fault_desc or "").strip()

    # Zorunlu alanlar
    if not first_name or not last_name:
        return RedirectResponse("/servis-talebi?err=Ad ve soyad zorunludur.", 303)
    if len(_digits(phone)) < 10:
        return RedirectResponse(
            "/servis-talebi?err=Geçerli bir telefon numarası girin (en az 10 hane).", 303)
    if not serial_no:
        return RedirectResponse("/servis-talebi?err=Makine seri numarası zorunludur.", 303)
    if len(fault_desc) < 10:
        return RedirectResponse(
            "/servis-talebi?err=Lütfen arızayı biraz daha ayrıntılı açıklayın.", 303)

    # Kayıt önce açılır ki resim adları id ile eşleşsin
    rid, ref = fdb.add_service_request(
        serial_no, model_name, fault_desc, "[]",
        first_name, last_name, phone, (email or "").strip(),
        (company_name or "").strip())

    saved = []
    for f in (photos or []):
        if len(saved) >= MAX_IMAGES:
            break
        fname = f.filename or ""
        ext = fname.rsplit(".", 1)[-1].lower() if "." in fname else ""
        if ext not in IMAGE_EXTS:
            continue
        data = await f.read()
        if not data or len(data) > MAX_IMAGE_MB * 1024 * 1024:
            continue
        try:
            saved.append(await run_in_threadpool(_save_image, data, f"{rid}", len(saved) + 1))
        except Exception:
            continue      # bozuk/resim olmayan dosyayı sessizce atla

    if saved:
        with fdb._c() as c:
            c.execute("UPDATE service_requests SET images_json=? WHERE id=?",
                      (json.dumps(saved), rid))

    try:
        from email_utils import send_admin_notification
        send_admin_notification("Yeni Servis Talebi", {
            "Referans": ref,
            "Ad Soyad": f"{first_name} {last_name}",
            "Telefon": phone,
            "E-posta": email or "-",
            "Firma": company_name or "-",
            "Seri No": serial_no,
            "Model": model_name or "-",
            "Arıza": fault_desc[:500],
            "Fotoğraf": f"{len(saved)} adet",
        })
    except Exception:
        pass

    return RedirectResponse(f"/servis-talebi/tesekkurler?ref={ref}", 303)


@router.get("/servis-talebi/tesekkurler")
async def service_thanks(request: Request, ref: str = ""):
    company = fdb.get_company() or {}
    return templates.TemplateResponse(request, "service_request_thanks.html", {
        "user": None,
        "company": company,
        "ref": ref,
    })


# ══════════════════════════════════════════════════════════════════════════
#  Yönetici tarafı — Talepler sayfası altında
# ══════════════════════════════════════════════════════════════════════════

@router.get("/admin/requests/servis/{rid}")
async def service_detail(request: Request, rid: int):
    user = auth.require_admin(request)
    req = fdb.get_service_request(rid)
    if not req:
        return RedirectResponse("/admin/requests?msg=Talep+bulunamadı&msg_type=error", 303)
    if req["status"] == "Yeni":
        fdb.upd_service_request(rid, status="İnceleniyor")
        req["status"] = "İnceleniyor"
    req["images"] = _images(req)
    return templates.TemplateResponse(request, "service_request_detail.html", {
        "user": user,
        "req": req,
        "statuses": fdb.SERVICE_STATUSES,
        "active_page": "admin_requests",
    })


@router.get("/admin/requests/servis/{rid}/resim/{idx}")
async def service_image(request: Request, rid: int, idx: int):
    auth.require_admin(request)
    req = fdb.get_service_request(rid)
    if not req:
        return Response(status_code=404)
    imgs = _images(req)
    if idx < 1 or idx > len(imgs):
        return Response(status_code=404)
    path = os.path.join(SERVICE_DIR, os.path.basename(imgs[idx - 1]))
    if not os.path.exists(path):
        return Response(status_code=404)
    with open(path, "rb") as f:
        return Response(f.read(), media_type="image/jpeg",
                        headers={"Cache-Control": "private, max-age=600"})


@router.post("/admin/requests/servis/{rid}/status")
async def service_status(request: Request, rid: int,
                         status: str = Form(""),
                         admin_note: str = Form("")):
    auth.require_admin(request)
    req = fdb.get_service_request(rid)
    if not req:
        return RedirectResponse("/admin/requests?msg=Talep+bulunamadı&msg_type=error", 303)
    # Tanınmayan bir değer gelirse mevcut durumu koru — sıfırlama
    if status not in fdb.SERVICE_STATUSES:
        status = req["status"]
    fdb.upd_service_request(rid, status=status, admin_note=admin_note.strip())
    return RedirectResponse(f"/admin/requests/servis/{rid}", 303)


@router.post("/admin/requests/servis/{rid}/delete")
async def service_delete(request: Request, rid: int):
    auth.require_admin(request)
    req = fdb.get_service_request(rid)
    if req:
        for name in _images(req):
            try:
                os.remove(os.path.join(SERVICE_DIR, os.path.basename(name)))
            except OSError:
                pass
        fdb.del_service_request(rid)
    return RedirectResponse("/admin/requests?msg=Servis+talebi+silindi&msg_type=info", 303)
