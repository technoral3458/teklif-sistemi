import urllib.request
import xml.etree.ElementTree as ET
import base64
import json
import math as _math
import os
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Request, Form, UploadFile, File
from fastapi.responses import RedirectResponse, JSONResponse, Response

import db.factory as fdb
import auth
from tmpl import templates


# ── NC Code Generator ─────────────────────────────────────────────────────────

def _eval_expr(expr, variables):
    """Safely evaluate a parametric expression using the given variables."""
    env = {k: float(v) for k, v in variables.items()}
    env.update({k: getattr(_math, k) for k in dir(_math) if not k.startswith("_")})
    env["__builtins__"] = None
    return float(eval(str(expr).strip(), env))


def _generate_nc(model, paths, variables):
    """Generate Fanuc-compatible G-code from a cap model and plate variables."""
    ev = lambda expr: _eval_expr(expr, variables)
    lines = []
    name_upper = model["name"].upper().replace("(", "").replace(")", "")
    var_comment = " ".join(f"{k}={v}" for k, v in sorted(variables.items()))
    safe_z = float(model.get("safe_z") or 5.0)
    feed_xy = int(model.get("feed_xy") or 3000)
    feed_z = int(model.get("feed_z") or 1000)
    spindle = int(model.get("spindle_speed") or 18000)
    tool_no = int(model.get("tool_no") or 1)

    lines += [
        "%",
        f"O0001 ({name_upper})",
        f"({var_comment})",
        f"(GENERATED {datetime.now().strftime('%Y-%m-%d %H:%M')})",
        "G17 G21 G40 G49 G80 G90",
        f"T{tool_no} M6",
        f"S{spindle} M3",
        f"G0 G90 Z{safe_z:.3f}",
    ]

    for p in paths:
        label = (p.get("label") or "").strip()
        ptype = p.get("path_type", "LINE")
        if label:
            lines.append(f"({label})")

        try:
            x1, y1 = ev(p["x1"]), ev(p["y1"])
            x2, y2 = ev(p["x2"]), ev(p["y2"])
            z2 = ev(p["z2"])
            feed = int(ev(p["feed_override"])) if str(p.get("feed_override", "")).strip() else feed_xy

            if ptype == "LINE":
                lines += [
                    f"G0 Z{safe_z:.3f}",
                    f"G0 X{x1:.3f} Y{y1:.3f}",
                    f"G1 Z{z2:.3f} F{feed_z}",
                    f"G1 X{x2:.3f} Y{y2:.3f} F{feed}",
                ]

            elif ptype in ("ARC_CW", "ARC_CCW"):
                cx, cy = ev(p.get("ix") or "0"), ev(p.get("jy") or "0")
                I = round(cx - x1, 3)
                J = round(cy - y1, 3)
                cmd = "G2" if ptype == "ARC_CW" else "G3"
                lines += [
                    f"G0 Z{safe_z:.3f}",
                    f"G0 X{x1:.3f} Y{y1:.3f}",
                    f"G1 Z{z2:.3f} F{feed_z}",
                    f"{cmd} X{x2:.3f} Y{y2:.3f} I{I:.3f} J{J:.3f} F{feed}",
                ]

            elif ptype == "POCKET":
                tool_dia = float(p.get("tool_dia") or 8.0)
                step_over = float(p.get("step_over") or 0.5)
                step = max(0.1, tool_dia * step_over)
                r = tool_dia / 2.0
                # Ensure x1<x2, y1<y2
                lx, rx = (min(x1,x2)+r, max(x1,x2)-r)
                by, ty = (min(y1,y2)+r, max(y1,y2)-r)
                lines.append(f"G0 Z{safe_z:.3f}")
                direction = 1
                y = by
                while y <= ty + 0.001:
                    sx, ex = (lx, rx) if direction == 1 else (rx, lx)
                    lines += [
                        f"G0 X{sx:.3f} Y{y:.3f}",
                        f"G1 Z{z2:.3f} F{feed_z}",
                        f"G1 X{ex:.3f} F{feed}",
                        f"G0 Z{safe_z:.3f}",
                    ]
                    y = round(y + step, 4)
                    direction *= -1
                # Contour finish pass
                lines += [
                    f"G0 X{lx:.3f} Y{by:.3f}",
                    f"G1 Z{z2:.3f} F{feed_z}",
                    f"G1 X{rx:.3f} F{feed}",
                    f"G1 Y{ty:.3f}",
                    f"G1 X{lx:.3f}",
                    f"G1 Y{by:.3f}",
                    f"G0 Z{safe_z:.3f}",
                ]

        except Exception as exc:
            lines.append(f"(ERROR IN PATH '{label or ptype}': {exc})")

    lines += [
        f"G0 Z{safe_z:.3f}",
        "M5",
        "G28 G91 Z0.",
        "M30",
        "%",
    ]
    return "\n".join(lines)

router = APIRouter(prefix="/membrane")


def _fetch_live_rates():
    try:
        url = "https://www.tcmb.gov.tr/kurlar/today.xml"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            data = r.read()
        root = ET.fromstring(data)
        result = {}
        for cur_el in root.findall("Currency"):
            code = cur_el.get("CurrencyCode") or cur_el.get("Kod", "")
            if code not in ("USD", "EUR", "GBP"):
                continue
            unit_el = cur_el.find("Unit")
            unit = int(unit_el.text) if unit_el is not None and unit_el.text else 1
            selling_el = cur_el.find("ForexSelling")
            if selling_el is not None and selling_el.text:
                rate = float(selling_el.text.replace(",", ".")) / unit
                result[code] = round(rate, 4)
        return result, None
    except Exception as e:
        return None, str(e)


def _calc_price_try(price, currency, rates):
    if currency == "TRY":
        return float(price)
    r = rates.get(currency, {}).get("rate", 1) or 1
    return float(price) * float(r)


def _material_cost_per_m2(mat, rates):
    price_try = _calc_price_try(mat["price"], mat["currency"], rates)
    if mat["unit"] == "plaka":
        w = float(mat["sheet_width"] or 0)
        h = float(mat["sheet_height"] or 0)
        area = (w / 100) * (h / 100)
        price_per_m2 = price_try / area if area > 0 else 0
    elif mat["unit"] == "m2":
        price_per_m2 = price_try
    else:
        price_per_m2 = price_try * float(mat["usage_per_m2"] or 0)
    return price_per_m2


def _enrich_doors(doors, total_cost_per_m2):
    for door in doors:
        area = (float(door["width_mm"]) / 1000) * (float(door["height_mm"]) / 1000)
        door["area_m2"] = round(area, 4)
        door["unit_cost"] = round(total_cost_per_m2 * area, 2)
        door["total_cost"] = round(door["unit_cost"] * int(door["quantity"]), 2)
    return doors


def _base_ctx(user, materials, rates):
    for mat in materials:
        mat["cost_per_m2_try"] = _material_cost_per_m2(mat, rates)
    total_cost_per_m2 = sum(m["cost_per_m2_try"] for m in materials)
    return materials, rates, round(total_cost_per_m2, 2)


# ── Main page: materials + rates + lists overview ─────────────────────────────

@router.get("")
async def membrane_page(request: Request):
    user = auth.require_user(request)
    materials = fdb.get_membrane_materials()
    rates = fdb.get_membrane_rates()
    materials, rates, total_cost_per_m2 = _base_ctx(user, materials, rates)

    lists = fdb.get_membrane_lists()
    for lst in lists:
        doors = fdb.get_membrane_doors_by_list(lst["id"])
        lst["total_cost"] = round(sum(
            total_cost_per_m2 * (float(d["width_mm"])/1000) * (float(d["height_mm"])/1000) * int(d["quantity"])
            for d in doors
        ), 2)

    return templates.TemplateResponse(request, "membrane_cost.html", {
        "user": user, "materials": materials, "rates": rates,
        "total_cost_per_m2": total_cost_per_m2, "lists": lists,
        "active_page": "membrane",
    })


# ── Rates ─────────────────────────────────────────────────────────────────────

@router.post("/rates/fetch")
async def fetch_rates(request: Request):
    user = auth.require_user(request)
    result, err = _fetch_live_rates()
    if result:
        for cur, rate in result.items():
            fdb.set_membrane_rate(cur, rate)
        msg, msg_type = f"Merkez Bankası kurları güncellendi ({', '.join(f'{c}: {r:.4f} ₺' for c,r in result.items())})", "success"
    else:
        msg, msg_type = f"Merkez Bankası'na bağlanılamadı: {err}. Kurları elle giriniz.", "danger"
    materials = fdb.get_membrane_materials()
    rates = fdb.get_membrane_rates()
    materials, rates, total_cost_per_m2 = _base_ctx(user, materials, rates)
    lists = fdb.get_membrane_lists()
    for lst in lists:
        doors = fdb.get_membrane_doors_by_list(lst["id"])
        lst["total_cost"] = round(sum(
            total_cost_per_m2 * (float(d["width_mm"])/1000) * (float(d["height_mm"])/1000) * int(d["quantity"])
            for d in doors
        ), 2)
    return templates.TemplateResponse(request, "membrane_cost.html", {
        "user": user, "materials": materials, "rates": rates,
        "total_cost_per_m2": total_cost_per_m2, "lists": lists,
        "active_page": "membrane", "msg": msg, "msg_type": msg_type,
    })


@router.post("/rates/save")
async def save_rates(request: Request,
                     usd: float = Form(0), eur: float = Form(0), gbp: float = Form(0)):
    auth.require_user(request)
    if usd > 0: fdb.set_membrane_rate("USD", usd)
    if eur > 0: fdb.set_membrane_rate("EUR", eur)
    if gbp > 0: fdb.set_membrane_rate("GBP", gbp)
    return RedirectResponse("/membrane", 303)


# ── Materials ─────────────────────────────────────────────────────────────────

@router.post("/material/save")
async def save_material(request: Request,
                        id: int = Form(0), name: str = Form(...),
                        material_type: str = Form("other"), price: float = Form(0),
                        currency: str = Form("TRY"), unit: str = Form("m2"),
                        sheet_width: float = Form(0), sheet_height: float = Form(0),
                        usage_per_m2: float = Form(1), notes: str = Form("")):
    auth.require_user(request)
    fdb.save_membrane_material(
        id=id or None, name=name, material_type=material_type,
        price=price, currency=currency, unit=unit,
        sheet_width=sheet_width, sheet_height=sheet_height,
        usage_per_m2=usage_per_m2, notes=notes,
    )
    return RedirectResponse("/membrane", 303)


@router.post("/material/delete")
async def delete_material(request: Request, id: int = Form(...)):
    auth.require_user(request)
    fdb.del_membrane_material(id)
    return RedirectResponse("/membrane", 303)


# ── Lists ─────────────────────────────────────────────────────────────────────

@router.post("/list/save")
async def save_list(request: Request, id: int = Form(0),
                    name: str = Form(...), notes: str = Form("")):
    auth.require_user(request)
    lid = fdb.save_membrane_list(id=id or None, name=name, notes=notes)
    return RedirectResponse(f"/membrane/list/{lid}", 303)


@router.post("/list/delete")
async def delete_list(request: Request, id: int = Form(...)):
    auth.require_user(request)
    fdb.del_membrane_list(id)
    return RedirectResponse("/membrane", 303)


# ── List Detail ───────────────────────────────────────────────────────────────

@router.get("/list/{lid}")
async def list_detail(request: Request, lid: int):
    user = auth.require_user(request)
    lst = fdb.get_membrane_list(lid)
    if not lst:
        return RedirectResponse("/membrane", 303)
    materials = fdb.get_membrane_materials()
    rates = fdb.get_membrane_rates()
    materials, rates, total_cost_per_m2 = _base_ctx(user, materials, rates)
    doors = _enrich_doors(fdb.get_membrane_doors_by_list(lid), total_cost_per_m2)
    grand_total = sum(d["total_cost"] for d in doors)
    grand_area = sum(d["area_m2"] * d["quantity"] for d in doors)
    return templates.TemplateResponse(request, "membrane_list.html", {
        "user": user, "lst": lst, "doors": doors, "materials": materials,
        "rates": rates, "total_cost_per_m2": total_cost_per_m2,
        "grand_total": round(grand_total, 2), "grand_area": round(grand_area, 4),
        "active_page": "membrane",
    })


@router.get("/list/{lid}/print")
async def print_list(request: Request, lid: int):
    user = auth.require_user(request)
    lst = fdb.get_membrane_list(lid)
    if not lst:
        return RedirectResponse("/membrane", 303)
    materials = fdb.get_membrane_materials()
    rates = fdb.get_membrane_rates()
    materials, rates, total_cost_per_m2 = _base_ctx(user, materials, rates)
    doors = _enrich_doors(fdb.get_membrane_doors_by_list(lid), total_cost_per_m2)
    grand_total = sum(d["total_cost"] for d in doors)
    grand_area = sum(d["area_m2"] * d["quantity"] for d in doors)
    company = fdb.get_company()
    return templates.TemplateResponse(request, "membrane_print.html", {
        "user": user, "lst": lst, "doors": doors, "company": company,
        "total_cost_per_m2": total_cost_per_m2,
        "grand_total": round(grand_total, 2), "grand_area": round(grand_area, 4),
    })


@router.post("/list/{lid}/door/save")
async def save_door(request: Request, lid: int,
                    id: int = Form(0), project_name: str = Form(""),
                    door_name: str = Form(""), width_mm: float = Form(...),
                    height_mm: float = Form(...), quantity: int = Form(1)):
    auth.require_user(request)
    fdb.save_membrane_door(
        id=id or None, project_name=project_name, door_name=door_name,
        width_mm=width_mm, height_mm=height_mm, quantity=quantity, list_id=lid,
    )
    return RedirectResponse(f"/membrane/list/{lid}", 303)


@router.post("/list/{lid}/door/delete")
async def delete_door(request: Request, lid: int, id: int = Form(...)):
    auth.require_user(request)
    fdb.del_membrane_door(id)
    return RedirectResponse(f"/membrane/list/{lid}", 303)


@router.post("/list/{lid}/door/clear")
async def clear_doors(request: Request, lid: int):
    auth.require_user(request)
    for door in fdb.get_membrane_doors_by_list(lid):
        fdb.del_membrane_door(door["id"])
    return RedirectResponse(f"/membrane/list/{lid}", 303)


@router.post("/list/{lid}/door/scan")
async def scan_image(request: Request, lid: int, image: UploadFile = File(...)):
    auth.require_user(request)

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return JSONResponse({"error": "ANTHROPIC_API_KEY ayarlanmamış. Sunucuda bu ortam değişkenini tanımlayın."}, status_code=500)

    content = await image.read()
    b64 = base64.standard_b64encode(content).decode()
    mime = image.content_type or "image/jpeg"

    prompt = """Bu görselde Türk mobilya/mutfak sektörüne ait el yazısıyla yazılmış membran kapak ölçü listesi var.
Tüm satırları tek tek oku ve kapak ölçülerini JSON array olarak çıkar.

OKUMA KURALLARI (çok önemli):
1. FORMAT: Genellikle "Boy x En = Adet" ya da "En x Boy = Adet" sırasında yazılır.
   Sütun başlıklarına bak (Boy/En/Adet gibi) — yoksa bağlamdan anla.
2. AYRAÇLAR: "x", "X", "×" ölçü ayracı; "=" ya da "-" ise adeti gösterir.
   Örn: "85X38=8" → boy=85, en=38, adet=8
3. ÖLÇÜ BİRİMİ TESPİTİ:
   - 2 haneli sayılar (10-99): büyük ihtimalle cm → mm'ye çevir (×10)
   - 3 haneli sayılar (100-999): büyük ihtimalle mm → direkt kullan
   - Şüpheliyse: tipik kapak en 150-1200mm, boy 150-2500mm aralığında olur
4. KESME / TAKSIM İŞARETİ: "/" rakamın parçası olabilir.
   Örn: "29/2" → 292, "11'5" veya "11.5" → 115, "14X59/7" → en=14cm=140mm, boy=597mm
5. ÜZERİ ÇİZİLİ SATIRLARI ATLA — iptal edilmiştir.
6. RENK/MODEL NOTU: Sayfanın kenarında renk kodu veya model adı varsa
   (örn: "STN Mercan", "Beyaz", "VR-805") tüm kapaklar için color alanına yaz.
7. AÇIKLAMALAR: "Tay lazım", "baca", "topuz" gibi notlar door_name'e yaz, ölçü olarak alma.

ÇIKTI — yalnızca geçerli JSON array döndür, başka hiçbir şey yazma:
[
  {"width_mm": 380, "height_mm": 850, "quantity": 8, "door_name": "", "color": "STN Mercan"},
  {"width_mm": 650, "height_mm": 250, "quantity": 1, "door_name": "", "color": "STN Mercan"}
]"""

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": mime, "data": b64}},
                    {"type": "text", "text": prompt},
                ],
            }],
        )
        raw = response.content[0].text.strip()
        start = raw.find("[")
        end = raw.rfind("]") + 1
        if start == -1 or end == 0:
            return JSONResponse({"error": f"Model ölçü listesi bulamadı. Ham yanıt: {raw[:400]}"}, status_code=422)
        doors = json.loads(raw[start:end])
        saved = []
        for d in doors:
            w = float(d.get("width_mm") or 0)
            h = float(d.get("height_mm") or 0)
            if w <= 0 or h <= 0:
                continue
            name = str(d.get("door_name") or "")
            color = str(d.get("color") or "")
            full_name = f"{name} - {color}".strip(" -") if (name or color) else ""
            fdb.save_membrane_door(
                project_name="", door_name=full_name,
                width_mm=w, height_mm=h,
                quantity=max(1, int(d.get("quantity") or 1)),
                list_id=lid,
            )
            saved.append({"width_mm": w, "height_mm": h,
                          "quantity": int(d.get("quantity") or 1),
                          "door_name": full_name, "color": color})
        return JSONResponse({"saved": saved, "count": len(saved)})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# Keep old routes for backward compatibility
@router.post("/door/save")
async def save_door_old(request: Request, id: int = Form(0),
                        project_name: str = Form(""), door_name: str = Form(""),
                        width_mm: float = Form(...), height_mm: float = Form(...),
                        quantity: int = Form(1)):
    auth.require_user(request)
    fdb.save_membrane_door(
        id=id or None, project_name=project_name, door_name=door_name,
        width_mm=width_mm, height_mm=height_mm, quantity=quantity,
    )
    return RedirectResponse("/membrane", 303)


@router.post("/door/delete")
async def delete_door_old(request: Request, id: int = Form(...)):
    auth.require_user(request)
    fdb.del_membrane_door(id)
    return RedirectResponse("/membrane", 303)


# ── Parametric Cap Models ─────────────────────────────────────────────────────

@router.get("/caps")
async def caps_list(request: Request):
    user = auth.require_user(request)
    models = fdb.get_cap_models()
    return templates.TemplateResponse(request, "membrane_caps.html", {
        "user": user, "models": models, "active_page": "membrane",
        "edit_model": None, "paths": [],
        "msg": request.query_params.get("msg", ""),
        "msg_type": request.query_params.get("msg_type", "info"),
    })


@router.get("/caps/{mid}")
async def caps_edit(request: Request, mid: int):
    user = auth.require_user(request)
    model = fdb.get_cap_model(mid)
    if not model:
        return RedirectResponse("/membrane/caps", 303)
    paths = fdb.get_cap_paths(mid)
    models = fdb.get_cap_models()
    return templates.TemplateResponse(request, "membrane_caps.html", {
        "user": user, "models": models, "edit_model": model, "paths": paths,
        "active_page": "membrane",
        "msg": request.query_params.get("msg", ""),
        "msg_type": request.query_params.get("msg_type", "info"),
    })


@router.post("/caps/save")
async def caps_save(request: Request,
                    id: int = Form(0),
                    name: str = Form(...),
                    description: str = Form(""),
                    tool_no: int = Form(1),
                    spindle_speed: int = Form(18000),
                    feed_xy: int = Form(3000),
                    feed_z: int = Form(1000),
                    safe_z: float = Form(5.0),
                    constants_json: str = Form("{}")):
    auth.require_user(request)
    try:
        json.loads(constants_json or "{}")
    except Exception:
        constants_json = "{}"
    mid = fdb.save_cap_model(
        id=id or 0, name=name, description=description,
        tool_no=tool_no, spindle_speed=spindle_speed,
        feed_xy=feed_xy, feed_z=feed_z, safe_z=safe_z,
        constants_json=constants_json,
    )
    return RedirectResponse(f"/membrane/caps/{mid}?msg=Model+kaydedildi&msg_type=success", 303)


@router.post("/caps/delete")
async def caps_delete(request: Request, id: int = Form(...)):
    auth.require_user(request)
    fdb.del_cap_model(id)
    return RedirectResponse("/membrane/caps?msg=Model+silindi&msg_type=success", 303)


@router.post("/caps/{mid}/path/save")
async def cap_path_save(request: Request, mid: int,
                        id: int = Form(0),
                        seq: int = Form(0),
                        label: str = Form(""),
                        path_type: str = Form("LINE"),
                        x1: str = Form("0"), y1: str = Form("0"), z1: str = Form("0"),
                        x2: str = Form("W"), y2: str = Form("H"), z2: str = Form("-T"),
                        ix: str = Form("0"), jy: str = Form("0"),
                        tool_dia: float = Form(8.0),
                        step_over: float = Form(0.5),
                        feed_override: str = Form("")):
    auth.require_user(request)
    fdb.save_cap_path(
        id=id or 0, model_id=mid, seq=seq, label=label, path_type=path_type,
        x1=x1, y1=y1, z1=z1, x2=x2, y2=y2, z2=z2,
        ix=ix, jy=jy, tool_dia=tool_dia, step_over=step_over, feed_override=feed_override,
    )
    return RedirectResponse(f"/membrane/caps/{mid}?msg=Yol+kaydedildi&msg_type=success", 303)


@router.post("/caps/{mid}/path/delete")
async def cap_path_delete(request: Request, mid: int, path_id: int = Form(...)):
    auth.require_user(request)
    fdb.del_cap_path(path_id)
    return RedirectResponse(f"/membrane/caps/{mid}?msg=Yol+silindi&msg_type=success", 303)


@router.post("/caps/{mid}/generate")
async def cap_generate(request: Request, mid: int,
                       W: float = Form(0), H: float = Form(0), T: float = Form(18.0),
                       extra_json: str = Form("{}")):
    auth.require_user(request)
    model = fdb.get_cap_model(mid)
    if not model:
        return JSONResponse({"error": "Model bulunamadı"}, status_code=404)
    paths = fdb.get_cap_paths(mid)
    variables = {"W": W, "H": H, "T": T}
    try:
        extra = json.loads(extra_json or "{}")
        variables.update({k: float(v) for k, v in extra.items()})
    except Exception:
        pass
    constants = model.get("constants") or {}
    variables.update({k: float(v) for k, v in constants.items()})
    nc = _generate_nc(model, paths, variables)
    return JSONResponse({"nc": nc})


@router.get("/caps/{mid}/download")
async def cap_download(request: Request, mid: int,
                       W: float = 0, H: float = 0, T: float = 18.0,
                       extra: str = "{}"):
    auth.require_user(request)
    model = fdb.get_cap_model(mid)
    if not model:
        return RedirectResponse("/membrane/caps", 303)
    paths = fdb.get_cap_paths(mid)
    variables = {"W": W, "H": H, "T": T}
    try:
        variables.update({k: float(v) for k, v in json.loads(extra).items()})
    except Exception:
        pass
    variables.update({k: float(v) for k, v in (model.get("constants") or {}).items()})
    nc = _generate_nc(model, paths, variables)
    safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in model["name"])
    filename = f"{safe_name}_W{int(W)}xH{int(H)}.nc"
    return Response(
        content=nc,
        media_type="text/plain",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
