import urllib.request
import xml.etree.ElementTree as ET

from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse

import db.factory as fdb
import auth
from tmpl import templates

router = APIRouter(prefix="/membrane")


def _fetch_live_rates():
    """Fetch USD/EUR/GBP rates from TCMB (Merkez Bankası) XML feed."""
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
            # Use ForexSelling (döviz satış kuru)
            selling_el = cur_el.find("ForexSelling")
            if selling_el is not None and selling_el.text:
                rate = float(selling_el.text.replace(",", ".")) / unit
                result[code] = round(rate, 4)
        return result, None
    except Exception as e:
        return None, str(e)


def _calc_price_try(price, currency, rates):
    """Convert price in given currency to TRY."""
    if currency == "TRY":
        return float(price)
    r = rates.get(currency, {}).get("rate", 1) or 1
    return float(price) * float(r)


def _material_cost_per_m2(mat, rates):
    """Return cost per m² in TRY for a material."""
    price_try = _calc_price_try(mat["price"], mat["currency"], rates)
    if mat["unit"] == "plaka":
        w = float(mat["sheet_width"] or 0)
        h = float(mat["sheet_height"] or 0)
        area = (w / 100) * (h / 100)  # cm → m
        price_per_m2 = price_try / area if area > 0 else 0
    elif mat["unit"] == "m2":
        price_per_m2 = price_try
    else:
        # kg, lt, adet — use usage_per_m2
        price_per_m2 = price_try * float(mat["usage_per_m2"] or 0)
    return price_per_m2


@router.get("")
async def membrane_page(request: Request):
    user = auth.require_user(request)
    materials = fdb.get_membrane_materials()
    doors = fdb.get_membrane_doors()
    rates = fdb.get_membrane_rates()

    # Enrich materials with TRY cost per m²
    for mat in materials:
        mat["cost_per_m2_try"] = _material_cost_per_m2(mat, rates)

    total_cost_per_m2 = sum(m["cost_per_m2_try"] for m in materials)

    # Enrich doors with costs
    for door in doors:
        area = (float(door["width_mm"]) / 1000) * (float(door["height_mm"]) / 1000)
        door["area_m2"] = round(area, 4)
        door["unit_cost"] = round(total_cost_per_m2 * area, 2)
        door["total_cost"] = round(door["unit_cost"] * int(door["quantity"]), 2)

    return templates.TemplateResponse(request, "membrane_cost.html", {
        "user": user,
        "materials": materials,
        "doors": doors,
        "rates": rates,
        "total_cost_per_m2": round(total_cost_per_m2, 2),
        "active_page": "membrane",
    })


@router.post("/rates/fetch")
async def fetch_rates(request: Request):
    auth.require_user(request)
    result, err = _fetch_live_rates()
    if result:
        for cur, rate in result.items():
            fdb.set_membrane_rate(cur, rate)
        msg, msg_type = f"Merkez Bankası kurları güncellendi ({', '.join(f'{c}: {r:.4f} ₺' for c,r in result.items())})", "success"
    else:
        msg, msg_type = f"Merkez Bankası'na bağlanılamadı: {err}. Kurları elle giriniz.", "danger"
    materials = fdb.get_membrane_materials()
    doors = fdb.get_membrane_doors()
    rates = fdb.get_membrane_rates()
    for mat in materials:
        mat["cost_per_m2_try"] = _material_cost_per_m2(mat, rates)
    total_cost_per_m2 = sum(m["cost_per_m2_try"] for m in materials)
    for door in doors:
        area = (float(door["width_mm"]) / 1000) * (float(door["height_mm"]) / 1000)
        door["area_m2"] = round(area, 4)
        door["unit_cost"] = round(total_cost_per_m2 * area, 2)
        door["total_cost"] = round(door["unit_cost"] * int(door["quantity"]), 2)
    user = auth.require_user(request)
    return templates.TemplateResponse(request, "membrane_cost.html", {
        "user": user, "materials": materials, "doors": doors, "rates": rates,
        "total_cost_per_m2": round(total_cost_per_m2, 2),
        "active_page": "membrane", "msg": msg, "msg_type": msg_type,
    })


@router.post("/rates/save")
async def save_rates(request: Request,
                     usd: float = Form(0),
                     eur: float = Form(0),
                     gbp: float = Form(0)):
    auth.require_user(request)
    if usd > 0: fdb.set_membrane_rate("USD", usd)
    if eur > 0: fdb.set_membrane_rate("EUR", eur)
    if gbp > 0: fdb.set_membrane_rate("GBP", gbp)
    return RedirectResponse("/membrane", 303)


@router.post("/material/save")
async def save_material(request: Request,
                        id: int = Form(0),
                        name: str = Form(...),
                        material_type: str = Form("other"),
                        price: float = Form(0),
                        currency: str = Form("TRY"),
                        unit: str = Form("m2"),
                        sheet_width: float = Form(0),
                        sheet_height: float = Form(0),
                        usage_per_m2: float = Form(1),
                        notes: str = Form("")):
    auth.require_user(request)
    fdb.save_membrane_material(
        id=id or None,
        name=name, material_type=material_type,
        price=price, currency=currency,
        unit=unit, sheet_width=sheet_width, sheet_height=sheet_height,
        usage_per_m2=usage_per_m2, notes=notes,
    )
    return RedirectResponse("/membrane", 303)


@router.post("/material/delete")
async def delete_material(request: Request, id: int = Form(...)):
    auth.require_user(request)
    fdb.del_membrane_material(id)
    return RedirectResponse("/membrane", 303)


@router.post("/door/save")
async def save_door(request: Request,
                    id: int = Form(0),
                    project_name: str = Form(""),
                    door_name: str = Form(""),
                    width_mm: float = Form(...),
                    height_mm: float = Form(...),
                    quantity: int = Form(1)):
    auth.require_user(request)
    fdb.save_membrane_door(
        id=id or None,
        project_name=project_name, door_name=door_name,
        width_mm=width_mm, height_mm=height_mm, quantity=quantity,
    )
    return RedirectResponse("/membrane", 303)


@router.post("/door/delete")
async def delete_door(request: Request, id: int = Form(...)):
    auth.require_user(request)
    fdb.del_membrane_door(id)
    return RedirectResponse("/membrane", 303)


@router.post("/door/clear")
async def clear_doors(request: Request):
    auth.require_user(request)
    for door in fdb.get_membrane_doors():
        fdb.del_membrane_door(door["id"])
    return RedirectResponse("/membrane", 303)
