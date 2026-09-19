"""Parametrik kesim: 3B katı model → panel dilimleri → CNC için DXF."""

import json
import os
import re
import time

from fastapi import APIRouter, Request, Form, UploadFile, File
from fastapi.responses import RedirectResponse, Response, JSONResponse
from starlette.concurrency import run_in_threadpool

import auth
import db.factory as fdb
import parametric_slicer as ps
from config import DATA_DIR
from tmpl import templates

router = APIRouter(prefix="/parametric")

PARAM_DIR = os.path.join(DATA_DIR, "parametric")
os.makedirs(PARAM_DIR, exist_ok=True)

MAX_UPLOAD_MB = 60
ALLOWED_EXTS = {"stl", "obj"}
MAX_IMAGE_MB = 20
IMAGE_EXTS = {"png", "jpg", "jpeg", "webp", "bmp", "gif"}
AXES = [("z", "Z ekseni (dikey / yukarıdan aşağı)"),
        ("y", "Y ekseni (derinlik)"),
        ("x", "X ekseni (yatay / soldan sağa)")]


def _safe(s, default="model"):
    s = re.sub(r"[^A-Za-z0-9_\-]+", "_", (s or "").strip())
    return s.strip("_")[:60] or default


def _src_path(job):
    return os.path.join(PARAM_DIR, job["src_file"]) if job.get("src_file") else ""


def _res_path(jid):
    return os.path.join(PARAM_DIR, f"{jid}_panels.json.gz")


# Aynı modelin tekrar tekrar ayrıştırılmaması için küçük bellek içi önbellek
_MESH_CACHE = {}


def _load_mesh_cached(path):
    try:
        mtime = os.path.getmtime(path)
    except OSError:
        raise ValueError("Model dosyası bulunamadı. Lütfen yeniden yükleyin.")
    key = (path, mtime)
    hit = _MESH_CACHE.get(key)
    if hit is not None:
        return hit
    with open(path, "rb") as f:
        tris = ps.load_mesh(f.read(), path)
    _MESH_CACHE.clear()          # tek model yeterli — bellek şişmesin
    _MESH_CACHE[key] = tris
    return tris


def _load_result(jid):
    p = _res_path(jid)
    if not os.path.exists(p):
        return None
    with open(p, "rb") as f:
        return ps.load_result(f.read())


def _is_admin(user):
    return user.get("role") == "admin"


def _get_own_job(request, jid):
    """Oturumdaki kullanıcı + sahibi olduğu iş. Değilse (user, None) döner.

    Yönetici bütün işleri görebilir; diğer kullanıcılar yalnızca kendi
    yükledikleri dosyalara erişir.
    """
    user = auth.require_user(request)
    job = fdb.get_parametric_job(jid)
    if not job:
        return user, None
    if not _is_admin(user) and job.get("user_id") != user["id"]:
        return user, None          # başkasının işi — yokmuş gibi davran
    return user, job


# ── Liste + yükleme ───────────────────────────────────────────────────────────

@router.get("")
async def index(request: Request, msg: str = "", err: str = ""):
    user = auth.require_user(request)
    # Yönetici hepsini görür, diğer kullanıcılar yalnızca kendi işlerini
    jobs = (fdb.get_parametric_jobs() if _is_admin(user)
            else fdb.get_parametric_jobs(user["id"]))
    owners = {}
    if _is_admin(user):
        try:
            import db.users as udb
            owners = {u["id"]: (u.get("company_name") or u.get("email") or "—")
                      for u in udb.all_users()}
        except Exception:
            owners = {}
    for j in jobs:
        try:
            j["summary"] = json.loads(j.get("summary_json") or "{}")
        except Exception:
            j["summary"] = {}
        j["owner_name"] = owners.get(j.get("user_id"), "")
    return templates.TemplateResponse(request, "parametric.html", {
        "user": user,
        "is_admin": _is_admin(user),
        "jobs": jobs,
        "msg": msg,
        "err": err,
        "active_page": "parametric",
        "max_mb": MAX_UPLOAD_MB,
    })


@router.post("/upload")
async def upload(request: Request,
                 name: str = Form(""),
                 file: UploadFile = File(...)):
    user = auth.require_user(request)

    fname = file.filename or ""
    ext = fname.rsplit(".", 1)[-1].lower() if "." in fname else ""
    if ext not in ALLOWED_EXTS:
        return RedirectResponse(
            "/parametric?err=" + f"Sadece STL ve OBJ desteklenir ('.{ext}' yüklendi). "
            "CAD programınızdan STL olarak dışa aktarın.", 303)

    data = await file.read()
    if not data:
        return RedirectResponse("/parametric?err=Dosya boş.", 303)
    if len(data) > MAX_UPLOAD_MB * 1024 * 1024:
        return RedirectResponse(
            f"/parametric?err=Dosya çok büyük ({len(data)/1048576:.0f} MB). "
            f"Üst sınır {MAX_UPLOAD_MB} MB.", 303)

    try:
        tris = await run_in_threadpool(ps.load_mesh, data, fname)
    except ValueError as e:
        return RedirectResponse(f"/parametric?err={e}", 303)
    except Exception:
        return RedirectResponse(
            "/parametric?err=Model okunamadı. Dosyanın geçerli bir STL/OBJ olduğundan emin olun.", 303)

    title = (name or "").strip() or os.path.splitext(fname)[0]
    stored = f"{int(time.time())}_{_safe(title)}.{ext}"
    with open(os.path.join(PARAM_DIR, stored), "wb") as f:
        f.write(data)

    jid = fdb.add_parametric_job(user["id"], title, stored, fname, len(tris))
    return RedirectResponse(f"/parametric/{jid}", 303)


@router.post("/upload-image")
async def upload_image(request: Request,
                       name: str = Form(""),
                       file: UploadFile = File(...)):
    """Resim yükle → kabartma (relief) modunda iş oluştur."""
    user = auth.require_user(request)

    fname = file.filename or ""
    ext = fname.rsplit(".", 1)[-1].lower() if "." in fname else ""
    if ext not in IMAGE_EXTS:
        return RedirectResponse(
            f"/parametric?err=Desteklenmeyen resim biçimi ('.{ext}'). "
            "PNG, JPG veya WEBP kullanın.", 303)

    data = await file.read()
    if not data:
        return RedirectResponse("/parametric?err=Dosya boş.", 303)
    if len(data) > MAX_IMAGE_MB * 1024 * 1024:
        return RedirectResponse(
            f"/parametric?err=Resim çok büyük ({len(data)/1048576:.0f} MB). "
            f"Üst sınır {MAX_IMAGE_MB} MB.", 303)

    def probe():
        from PIL import Image
        import io as _io
        im = Image.open(_io.BytesIO(data))
        im.load()
        return im.size

    try:
        iw, ih = await run_in_threadpool(probe)
    except Exception:
        return RedirectResponse("/parametric?err=Resim okunamadı veya bozuk.", 303)

    title = (name or "").strip() or os.path.splitext(fname)[0]
    stored = f"{int(time.time())}_{_safe(title)}.{ext}"
    with open(os.path.join(PARAM_DIR, stored), "wb") as f:
        f.write(data)

    jid = fdb.add_parametric_job(user["id"], title, stored, fname, 0, src_kind="image")
    # Resmin en-boy oranını koruyan makul bir başlangıç ölçüsü öner
    w0 = 1200.0
    fdb.upd_parametric_job(jid, img_w=w0, img_h=round(w0 * ih / iw, 1) if iw else 800.0)
    return RedirectResponse(f"/parametric/{jid}", 303)


@router.get("/{jid}/image")
async def source_image(request: Request, jid: int):
    """Yüklenen kaynak resmi gösterir (data/ klasörü web'e açık değil)."""
    _user, job = _get_own_job(request, jid)
    if not job or job.get("src_kind") != "image":
        return Response(status_code=404)
    p = _src_path(job)
    if not p or not os.path.exists(p):
        return Response(status_code=404)
    ext = p.rsplit(".", 1)[-1].lower()
    mt = {"png": "image/png", "webp": "image/webp", "gif": "image/gif",
          "bmp": "image/bmp"}.get(ext, "image/jpeg")
    with open(p, "rb") as f:
        return Response(f.read(), media_type=mt,
                        headers={"Cache-Control": "private, max-age=600"})


@router.post("/{jid}/slice-image")
async def slice_image(request: Request, jid: int,
                      img_w: float = Form(1200.0),
                      img_h: float = Form(800.0),
                      img_depth: float = Form(180.0),
                      min_depth: float = Form(40.0),
                      thickness: float = Form(18.0),
                      gap: float = Form(0.0),
                      orient: str = Form("v"),
                      shape_mode: str = Form("single"),
                      invert: int = Form(0),
                      smooth: float = Form(1.0),
                      normalize: int = Form(0),
                      simplify_tol: float = Form(0.3),
                      hole_count: int = Form(2),
                      hole_dia: float = Form(10.0),
                      frame_count: int = Form(0),
                      frame_t: float = Form(18.0),
                      frame_h: float = Form(120.0),
                      frame_fit: float = Form(0.2),
                      sheet_w: float = Form(2100.0),
                      sheet_h: float = Form(2800.0),
                      part_gap: float = Form(15.0)):
    _user, job = _get_own_job(request, jid)
    if not job:
        return RedirectResponse("/parametric?err=Kayıt bulunamadı.", 303)
    if thickness <= 0:
        return RedirectResponse(f"/parametric/{jid}?err=Panel kalınlığı sıfırdan büyük olmalı.", 303)

    def work():
        from PIL import Image
        with Image.open(_src_path(job)) as im:
            im.load()
            res = ps.build_panels_from_image(
                im, width=img_w, height=img_h, depth=img_depth,
                min_depth=min_depth, thickness=thickness, gap=max(0.0, gap),
                orient=orient, invert=bool(invert), smooth=max(0.0, smooth),
                normalize=bool(normalize), shape=shape_mode,
                simplify_tol=max(0.0, simplify_tol),
                hole_count=max(0, hole_count), hole_dia=hole_dia)
        if frame_count > 0:
            ps.add_frames(res, count=frame_count, frame_t=frame_t,
                          frame_h=frame_h, fit=frame_fit)
        _, sheets, oversize = ps.export_dxf(
            res, sheet_w=sheet_w, sheet_h=sheet_h, part_gap=part_gap)
        return (res, sheets, oversize, ps.dump_result(res),
                ps.export_svg(res), ps.export_assembly_svg(res))

    try:
        res, sheets, oversize, blob, svg, asm = await run_in_threadpool(work)
    except ValueError as e:
        return RedirectResponse(f"/parametric/{jid}?err={e}", 303)
    except Exception as e:
        return RedirectResponse(f"/parametric/{jid}?err=Kabartma hatası: {e}", 303)

    with open(_res_path(jid), "wb") as f:
        f.write(blob)

    summ = ps.summary(res, sheets)
    if oversize:
        summ.setdefault("warnings", []).append(
            f"{len(oversize)} panel plakaya sığmıyor "
            f"(no: {', '.join(str(n) for n in oversize[:8])}). "
            "Plaka ölçüsünü büyütün veya işi küçültün.")

    fdb.upd_parametric_job(
        jid, img_w=img_w, img_h=img_h, img_depth=img_depth, min_depth=min_depth,
        thickness=thickness, gap=gap, orient=orient, shape_mode=shape_mode,
        invert=int(bool(invert)), smooth=smooth, normalize=int(bool(normalize)),
        simplify_tol=simplify_tol, hole_count=hole_count, hole_dia=hole_dia,
        frame_count=frame_count, frame_t=frame_t, frame_h=frame_h,
        frame_fit=frame_fit,
        sheet_w=sheet_w, sheet_h=sheet_h, part_gap=part_gap,
        panel_count=summ["panel_count"], sheet_count=sheets,
        summary_json=json.dumps(summ, default=float), svg=svg, asm_svg=asm,
        status="Hazır")

    return RedirectResponse(
        f"/parametric/{jid}?msg={summ['panel_count']} panel hazırlandı.", 303)


# ── Detay + dilimleme ─────────────────────────────────────────────────────────

@router.get("/{jid}")
async def detail(request: Request, jid: int, msg: str = "", err: str = ""):
    user, job = _get_own_job(request, jid)
    if not job:
        return RedirectResponse("/parametric?err=Kayıt bulunamadı.", 303)

    try:
        job["summary"] = json.loads(job.get("summary_json") or "{}")
    except Exception:
        job["summary"] = {}

    bounds = None       # 3B model sınırları (ölçek seçimine yardımcı olur)
    img_size = None     # resmin piksel ölçüsü ve en-boy oranı
    if job.get("src_kind") == "image":
        def probe():
            from PIL import Image
            with Image.open(_src_path(job)) as im:
                return im.size
        try:
            img_size = await run_in_threadpool(probe)
        except Exception:
            pass
    else:
        try:
            tris = await run_in_threadpool(_load_mesh_cached, _src_path(job))
            bounds = ps.mesh_info(tris)
        except Exception:
            pass

    tpl = ("parametric_image.html" if job.get("src_kind") == "image"
           else "parametric_detail.html")
    return templates.TemplateResponse(request, tpl, {
        "user": user,
        "job": job,
        "bounds": bounds,
        "img_size": img_size,
        "axes": AXES,
        "msg": msg,
        "err": err,
        "active_page": "parametric",
    })


@router.post("/{jid}/slice")
async def do_slice(request: Request, jid: int,
                   axis: str = Form("z"),
                   thickness: float = Form(18.0),
                   gap: float = Form(0.0),
                   scale: float = Form(1.0),
                   target_len: float = Form(0.0),
                   simplify_tol: float = Form(0.15),
                   hole_count: int = Form(2),
                   hole_dia: float = Form(10.0),
                   frame_count: int = Form(0),
                   frame_t: float = Form(18.0),
                   frame_h: float = Form(120.0),
                   frame_fit: float = Form(0.2),
                   sheet_w: float = Form(2100.0),
                   sheet_h: float = Form(2800.0),
                   part_gap: float = Form(15.0)):
    _user, job = _get_own_job(request, jid)
    if not job:
        return RedirectResponse("/parametric?err=Kayıt bulunamadı.", 303)

    if thickness <= 0:
        return RedirectResponse(f"/parametric/{jid}?err=Panel kalınlığı sıfırdan büyük olmalı.", 303)
    if gap < 0:
        gap = 0.0

    def work():
        tris = _load_mesh_cached(_src_path(job))
        sc = float(scale) if scale and scale > 0 else 1.0
        # "Hedef boy" verilmişse ölçek buradan hesaplanır
        if target_len and target_len > 0:
            span = ps.mesh_info(tris)["size"][ps._AXIS_IDX[axis if axis in ps._AXIS_IDX else "z"]]
            if span > 0:
                sc = target_len / span
        res = ps.build_panels(
            tris, axis=axis, thickness=thickness, gap=gap, scale=sc,
            simplify_tol=max(0.0, simplify_tol),
            hole_count=max(0, hole_count), hole_dia=hole_dia,
        )
        if frame_count > 0:
            ps.add_frames(res, count=frame_count, frame_t=frame_t,
                          frame_h=frame_h, fit=frame_fit)
        _, sheets, oversize = ps.export_dxf(
            res, sheet_w=sheet_w, sheet_h=sheet_h, part_gap=part_gap)
        return (res, sheets, oversize, ps.dump_result(res),
                ps.export_svg(res), ps.export_assembly_svg(res), sc)

    try:
        res, sheets, oversize, blob, svg, asm, sc = await run_in_threadpool(work)
    except ValueError as e:
        return RedirectResponse(f"/parametric/{jid}?err={e}", 303)
    except Exception as e:
        return RedirectResponse(f"/parametric/{jid}?err=Dilimleme hatası: {e}", 303)

    with open(_res_path(jid), "wb") as f:
        f.write(blob)

    summ = ps.summary(res, sheets)
    if oversize:
        summ.setdefault("warnings", []).append(
            f"{len(oversize)} panel plakaya sığmıyor "
            f"(no: {', '.join(str(n) for n in oversize[:8])}). "
            "Plaka ölçüsünü büyütün veya modeli küçültün.")

    fdb.upd_parametric_job(
        jid, axis=axis, thickness=thickness, gap=gap, scale=sc,
        simplify_tol=simplify_tol, hole_count=hole_count, hole_dia=hole_dia,
        frame_count=frame_count, frame_t=frame_t, frame_h=frame_h,
        frame_fit=frame_fit,
        sheet_w=sheet_w, sheet_h=sheet_h, part_gap=part_gap,
        panel_count=summ["panel_count"], sheet_count=sheets,
        summary_json=json.dumps(summ, default=float), svg=svg, asm_svg=asm,
        status="Hazır")

    return RedirectResponse(
        f"/parametric/{jid}?msg={summ['panel_count']} panel hazırlandı.", 303)


# ── İndirmeler ────────────────────────────────────────────────────────────────

@router.get("/{jid}/dxf")
async def download_dxf(request: Request, jid: int):
    _user, job = _get_own_job(request, jid)
    if not job:
        return RedirectResponse("/parametric?err=Kayıt bulunamadı.", 303)
    res = _load_result(jid)
    if not res:
        return RedirectResponse(f"/parametric/{jid}?err=Önce 'Dilimle' butonuna basın.", 303)

    dxf, _, _ = await run_in_threadpool(
        ps.export_dxf, res, job["sheet_w"], job["sheet_h"], job["part_gap"])
    fn = f"{_safe(job['name'])}_paneller.dxf"
    return Response(dxf, media_type="application/dxf",
                    headers={"Content-Disposition": f'attachment; filename="{fn}"'})


@router.get("/{jid}/zip")
async def download_zip(request: Request, jid: int):
    _user, job = _get_own_job(request, jid)
    if not job:
        return RedirectResponse("/parametric?err=Kayıt bulunamadı.", 303)
    res = _load_result(jid)
    if not res:
        return RedirectResponse(f"/parametric/{jid}?err=Önce 'Dilimle' butonuna basın.", 303)

    blob = await run_in_threadpool(ps.export_zip, res, True, _safe(job["name"]))
    fn = f"{_safe(job['name'])}_paneller.zip"
    return Response(blob, media_type="application/zip",
                    headers={"Content-Disposition": f'attachment; filename="{fn}"'})


@router.get("/{jid}/3d")
async def geometry_3d(request: Request, jid: int):
    """Fareyle döndürülebilir önizleme için katı geometri (JSON)."""
    _user, job = _get_own_job(request, jid)
    empty = {"parts": [], "bb": [0, 0, 0, 1, 1, 1]}
    if not job:
        return JSONResponse(empty, status_code=404)
    res = _load_result(jid)
    if not res:
        return JSONResponse(empty)
    data = await run_in_threadpool(ps.export_3d, res)
    return JSONResponse(data)


@router.post("/{jid}/delete")
async def delete(request: Request, jid: int):
    _user, job = _get_own_job(request, jid)
    if not job:
        return RedirectResponse("/parametric?err=Kayıt bulunamadı.", 303)
    for p in (_src_path(job), _res_path(jid)):
        try:
            if p and os.path.exists(p):
                os.remove(p)
        except OSError:
            pass
    fdb.del_parametric_job(jid)
    return RedirectResponse("/parametric?msg=Kayıt silindi.", 303)
