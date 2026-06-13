import os
import uuid
import json
from io import BytesIO
from typing import Optional

from fastapi import APIRouter, Request, Form, UploadFile, File
from fastapi.responses import JSONResponse, RedirectResponse, Response

import db.factory as fdb
import auth
from config import IMAGES_DIR, CURRENCIES

router = APIRouter(prefix="/models")
from tmpl import templates


def _calc_cost(purchase_price, shipping_cost, customs_pct, extra_tax_pct,
               port_cost, document_cost, installation_cost, other_cost):
    return (
        purchase_price + shipping_cost
        + purchase_price * customs_pct / 100
        + purchase_price * extra_tax_pct / 100
        + port_cost + document_cost + installation_cost + other_cost
    )


@router.get("")
async def models_list(request: Request, category_id: int = 0):
    user = auth.require_user(request)
    cats = fdb.get_cats()
    models = fdb.get_models(category_id if category_id else None)
    cat_map = {c["id"]: c["name"] for c in cats}
    for m in models:
        m["category_name"] = cat_map.get(m.get("category_id"), "-")
    return templates.TemplateResponse(request, "models.html", {
        "user": user,
        "models": models,
        "categories": cats,
        "selected_cat": category_id,
        "currencies": CURRENCIES,
        "active_page": "models",
    })


@router.get("/new")
async def model_new(request: Request):
    user = auth.require_user(request)
    cats = fdb.get_cats()
    options = fdb.get_options()
    return templates.TemplateResponse(request, "model_form.html", {
        "user": user,
        "model": {},
        "categories": cats,
        "options": options,
        "compatible_options_selected": [],
        "currencies": CURRENCIES,
        "active_page": "models",
        "line_images": {},
    })


@router.get("/{model_id}/edit")
async def model_edit(request: Request, model_id: int):
    user = auth.require_user(request)
    m = fdb.get_model(model_id)
    if not m:
        return RedirectResponse("/models", 303)
    cats = fdb.get_cats()
    options = fdb.get_options()
    compatible = []
    if m.get("compatible_options"):
        try:
            compatible = json.loads(m["compatible_options"])
        except Exception:
            pass
    line_images = fdb.get_model_line_images(model_id)
    return templates.TemplateResponse(request, "model_form.html", {
        "user": user,
        "model": m,
        "categories": cats,
        "options": options,
        "compatible_options_selected": compatible,
        "currencies": CURRENCIES,
        "active_page": "models",
        "line_images": {img["line_count"]: img for img in line_images},
    })


@router.post("/save")
async def save_model(request: Request,
                     id: int = Form(0),
                     name: str = Form(...),
                     category_id: int = Form(0),
                     description: str = Form(""),
                     base_price: float = Form(0.0),
                     currency: str = Form("USD"),
                     specs: str = Form(""),
                     purchase_price: float = Form(0.0),
                     purchase_currency: str = Form("USD"),
                     shipping_cost: float = Form(0.0),
                     customs_pct: float = Form(0.0),
                     extra_tax_pct: float = Form(0.0),
                     port_cost: float = Form(0.0),
                     document_cost: float = Form(0.0),
                     installation_cost: float = Form(0.0),
                     other_cost: float = Form(0.0),
                     image: Optional[UploadFile] = File(None),
                     name_en: str = Form(""),
                     description_en: str = Form(""),
                     name_zh: str = Form(""),
                     description_zh: str = Form(""),
                     specs_en: str = Form(""),
                     specs_zh: str = Form(""),
                     is_line: int = Form(0),
                     line_configs: str = Form("2,3,4")):
    auth.require_user(request)

    total_cost = _calc_cost(
        purchase_price, shipping_cost, customs_pct, extra_tax_pct,
        port_cost, document_cost, installation_cost, other_cost,
    )

    form_data = await request.form()
    compatible_ids = form_data.getlist("compatible_options")
    compatible_json = json.dumps([int(x) for x in compatible_ids if x])

    image_path = ""
    if image and image.filename:
        os.makedirs(IMAGES_DIR, exist_ok=True)
        ext = os.path.splitext(image.filename)[1].lower() or ".jpg"
        fname = f"{uuid.uuid4().hex}{ext}"
        fpath = os.path.join(IMAGES_DIR, fname)
        content = await image.read()
        try:
            from PIL import Image as PILImage
            import io as _io
            img = PILImage.open(_io.BytesIO(content))
            img.thumbnail((800, 800))
            img.save(fpath, "JPEG", quality=85)
        except Exception:
            with open(fpath, "wb") as f:
                f.write(content)
        image_path = f"img/uploads/{fname}"

    kw = dict(
        name=name,
        category_id=category_id or None,
        description=description,
        base_price=base_price,
        currency=currency,
        specs=specs,
        purchase_price=purchase_price,
        purchase_currency=purchase_currency,
        shipping_cost=shipping_cost,
        customs_pct=customs_pct,
        extra_tax_pct=extra_tax_pct,
        port_cost=port_cost,
        document_cost=document_cost,
        installation_cost=installation_cost,
        other_cost=other_cost,
        total_cost=total_cost,
        compatible_options=compatible_json,
        name_en=name_en,
        description_en=description_en,
        name_zh=name_zh,
        description_zh=description_zh,
        specs_en=specs_en,
        specs_zh=specs_zh,
        is_line=is_line,
        line_configs=line_configs.strip(),
    )
    if image_path:
        kw["image_path"] = image_path

    if id:
        fdb.upd_model(id, **kw)
        model_id = id
    else:
        model_id = fdb.add_model(**kw)

    # Save line images
    form_data = await request.form()
    for key in form_data.keys():
        if key.startswith("line_img_count_"):
            lc = int(key.replace("line_img_count_", ""))
            prio = int(form_data.get(f"line_img_prio_{lc}", 0) or 0)
            img_file = form_data.get(f"line_img_{lc}")
            if img_file and hasattr(img_file, "filename") and img_file.filename:
                ext = os.path.splitext(img_file.filename)[1].lower() or ".jpg"
                fname = f"line_{model_id}_{lc}_{uuid.uuid4().hex[:8]}{ext}"
                fpath = os.path.join(IMAGES_DIR, fname)
                content = await img_file.read()
                try:
                    from PIL import Image as PILImage
                    import io as _io
                    img_obj = PILImage.open(_io.BytesIO(content))
                    img_obj.thumbnail((800, 800))
                    img_obj.save(fpath, "JPEG", quality=85)
                except Exception:
                    with open(fpath, "wb") as f:
                        f.write(content)
                fdb.save_model_line_image(model_id, lc, f"img/uploads/{fname}", prio)
            else:
                # Update priority only if image already exists
                existing = fdb.get_model_line_images(model_id)
                for ei in existing:
                    if ei["line_count"] == lc:
                        fdb.save_model_line_image(model_id, lc, ei["image_path"], prio)

    return RedirectResponse("/models", 303)


@router.post("/spec-image")
async def upload_spec_image(request: Request, image: UploadFile = File(...)):
    auth.require_user(request)
    if not image or not image.filename:
        return JSONResponse({"error": "No file"}, status_code=400)
    os.makedirs(IMAGES_DIR, exist_ok=True)
    ext = os.path.splitext(image.filename)[1].lower() or ".jpg"
    fname = f"spec_{uuid.uuid4().hex[:10]}{ext}"
    content = await image.read()
    with open(os.path.join(IMAGES_DIR, fname), "wb") as f:
        f.write(content)
    return JSONResponse({"path": f"img/uploads/{fname}"})


@router.post("/line-image/delete")
async def delete_line_image(request: Request, id: int = Form(...), model_id: int = Form(...)):
    auth.require_user(request)
    fdb.del_model_line_image(id)
    return RedirectResponse(f"/models/{model_id}/edit", 303)


@router.post("/delete")
async def delete_model(request: Request, id: int = Form(...)):
    auth.require_user(request)
    fdb.del_model(id)
    return RedirectResponse("/models", 303)


@router.get("/excel-template")
async def excel_template_download(request: Request):
    auth.require_user(request)
    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment
    except ImportError:
        return Response("openpyxl kurulu değil. pip install openpyxl", status_code=500, media_type="text/plain")

    wb = openpyxl.Workbook()
    hdr_font  = Font(bold=True, color="FFFFFF")
    hdr_align_c = Alignment(horizontal="center", vertical="center", wrap_text=True)

    def _hdr(ws, col, value, fill_color, width, wrap=True):
        cell = ws.cell(row=1, column=col, value=value)
        cell.font      = hdr_font
        cell.fill      = PatternFill("solid", fgColor=fill_color)
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=wrap)
        col_letter = ws.cell(row=1, column=col).column_letter
        ws.column_dimensions[col_letter].width = width
        return cell

    # ── Sheet 1: Model temel bilgileri ────────────────────────────────────────
    ws1 = wb.active
    ws1.title = "Model Bilgileri"
    ws1.row_dimensions[1].height = 36

    info = [
        ("Makine Adı (TR) *", "2563EB", 28),
        ("Makine Adı (EN)",   "2563EB", 28),
        ("Makine Adı (ZH)",   "2563EB", 28),
        ("Açıklama (TR)",     "2563EB", 35),
        ("Açıklama (EN)",     "2563EB", 35),
        ("Açıklama (ZH)",     "2563EB", 35),
        ("Satış Fiyatı",      "2563EB", 14),
        ("Para Birimi\n(USD/EUR/TRY)", "2563EB", 16),
        ("Kategori Adı",      "2563EB", 22),
    ]
    for col, (title, color, width) in enumerate(info, 1):
        _hdr(ws1, col, title, color, width)

    # Not satırı
    note_cell = ws1.cell(row=2, column=1, value="⚠ Resimler Excel'e eklenemez — formdaki resim alanından yüklenir.")
    note_cell.font = Font(italic=True, color="B45309")
    ws1.merge_cells(start_row=2, start_column=1, end_row=2, end_column=9)

    # Örnek veri satırı
    example = ["Örnek Makine A", "Example Machine A", "", "Türkçe açıklama...", "English description...", "", 15000.00, "USD", "Kategori Adı"]
    for col, v in enumerate(example, 1):
        ws1.cell(row=3, column=col, value=v)

    # ── Sheet 2: Teknik özellikler ─────────────────────────────────────────────
    ws2 = wb.create_sheet("Teknik Özellikler")
    ws2.row_dimensions[1].height = 28

    spec_info = [
        ("Başlık",          "059669", 30),
        ("Açıklama (TR)",   "059669", 45),
        ("Açıklama (EN)",   "059669", 45),
        ("Açıklama (ZH)",   "059669", 45),
    ]
    for col, (title, color, width) in enumerate(spec_info, 1):
        _hdr(ws2, col, title, color, width)

    examples2 = [
        ("Motor Gücü",      "3.5 kW / 4.8 HP",    "Motor Power: 3.5 kW / 4.8 HP", ""),
        ("Kesim Genişliği", "1600 mm",             "Cutting Width: 1600 mm",        ""),
        ("Tabla Boyutu",    "1600 x 1250 mm",      "Table Size: 1600 x 1250 mm",    ""),
        ("Max. Kesim Hızı", "60 m/min",            "Max. Cutting Speed: 60 m/min",  ""),
        ("Ağırlık",         "850 kg",              "Weight: 850 kg",                ""),
    ]
    for row_idx, row_data in enumerate(examples2, 2):
        for col, v in enumerate(row_data, 1):
            ws2.cell(row=row_idx, column=col, value=v)

    # ── Sheet 3: Opsiyonlar ────────────────────────────────────────────────────
    ws3 = wb.create_sheet("Opsiyonlar")
    ws3.row_dimensions[1].height = 28

    opt_info = [
        ("ID",              "7C3AED", 8),
        ("Opsiyon Adı",     "7C3AED", 35),
        ("Fiyat",           "7C3AED", 12),
        ("Para Birimi",     "7C3AED", 12),
        ("Miktar Tipi",     "7C3AED", 16),
        ("Uyumlu? (E/H)",   "7C3AED", 16),
    ]
    for col, (title, color, width) in enumerate(opt_info, 1):
        _hdr(ws3, col, title, color, width)

    # Sistemdeki tüm opsiyonları listele
    options = fdb.get_options()
    qty_labels = {"MANUAL": "Elle Giriş", "FIXED_1": "Sabit 1", "PER_MACHINE": "Makine Adeti"}
    for row_idx, opt in enumerate(options, 2):
        ws3.cell(row=row_idx, column=1, value=opt["id"])
        ws3.cell(row=row_idx, column=2, value=opt.get("name", ""))
        ws3.cell(row=row_idx, column=3, value=opt.get("price", 0))
        ws3.cell(row=row_idx, column=4, value=opt.get("currency", ""))
        ws3.cell(row=row_idx, column=5, value=qty_labels.get(opt.get("qty_type", "MANUAL"), opt.get("qty_type", "")))
        ws3.cell(row=row_idx, column=6, value="H")  # default: uyumsuz

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    return Response(
        buf.read(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="model_sablonu.xlsx"'},
    )


@router.post("/excel-import")
async def excel_import(request: Request, excel_file: UploadFile = File(...)):
    auth.require_user(request)
    try:
        import openpyxl
    except ImportError:
        return JSONResponse({"error": "openpyxl kurulu değil"}, status_code=500)

    content = await excel_file.read()
    try:
        wb = openpyxl.load_workbook(BytesIO(content), data_only=True)
    except Exception as e:
        return JSONResponse({"error": f"Dosya okunamadı: {e}"}, status_code=400)

    result = {}

    # ── Sheet 1: Model bilgileri ──────────────────────────────────────────────
    ws1 = wb[wb.sheetnames[0]]
    # Row 2 = note/merge, row 3 = actual data
    data_row_idx = 3 if ws1.max_row >= 3 else 2
    keys1 = ["name", "name_en", "name_zh", "description", "description_en", "description_zh",
             "base_price", "currency", "category_name"]
    row_vals = [cell.value for cell in ws1[data_row_idx]]
    for k, v in zip(keys1, row_vals):
        if v is None:
            continue
        if k == "base_price":
            try:
                result[k] = float(v)
            except Exception:
                result[k] = 0.0
        else:
            s = str(v).strip()
            if s:
                result[k] = s

    # ── Sheet 2: Teknik özellikler (Başlık | TR | EN | ZH) ────────────────────
    def _sv(v):
        return str(v).strip() if v is not None else ""

    specs, specs_en, specs_zh = [], [], []
    if len(wb.sheetnames) > 1:
        ws2 = wb[wb.sheetnames[1]]
        for row in ws2.iter_rows(min_row=2, values_only=True):
            if not row or row[0] is None:
                continue
            title = _sv(row[0])
            if not title:
                continue
            desc    = _sv(row[1]) if len(row) > 1 else ""
            desc_en = _sv(row[2]) if len(row) > 2 else ""
            desc_zh = _sv(row[3]) if len(row) > 3 else ""
            specs.append(   {"title": title, "desc": desc,    "img": ""})
            specs_en.append({"title": title, "desc": desc_en, "img": ""})
            specs_zh.append({"title": title, "desc": desc_zh, "img": ""})

    result["specs"]    = specs
    result["specs_en"] = specs_en
    result["specs_zh"] = specs_zh

    # ── Sheet 3: Opsiyonlar ────────────────────────────────────────────────────
    compatible_ids = []
    if len(wb.sheetnames) > 2:
        ws3 = wb[wb.sheetnames[2]]
        for row in ws3.iter_rows(min_row=2, values_only=True):
            if not row or row[0] is None:
                continue
            opt_id = row[0]
            uyumlu = _sv(row[5]) if len(row) > 5 else "H"
            if uyumlu.upper() in ("E", "EVET", "YES", "1", "TRUE"):
                try:
                    compatible_ids.append(int(opt_id))
                except Exception:
                    pass

    result["compatible_option_ids"] = compatible_ids

    return JSONResponse(result)
