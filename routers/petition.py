"""Dilekçe — giriş gerektirmeyen, sade bir dilekçe yazma ve imzalama aracı.

Kullanıcı metni yazar, telefonun dokunmatik ekranında imzalar, PDF üretilir ve
WhatsApp'tan paylaşılır. Sunucuda hiçbir şey saklanmaz; PDF anında üretilip
doğrudan kullanıcıya döner.
"""

import base64
import re
from datetime import datetime

from fastapi import APIRouter, Request, Form
from fastapi.responses import Response

from tmpl import templates
from translations import TRANSLATIONS

router = APIRouter(prefix="/dilekce")

LANGS = ("tr", "en", "zh")
MAX_TEXT = 20000           # karakter
MAX_SIG_BYTES = 2 * 1024 * 1024
_SIG_RE = re.compile(r"^data:image/png;base64,([A-Za-z0-9+/=\s]+)$")


def _i18n():
    return {lg: {k: v for k, v in TRANSLATIONS.get(lg, {}).items()
                 if k.startswith("pt_")} for lg in LANGS}


def _msg(lang, key):
    lang = lang if lang in LANGS else "tr"
    return TRANSLATIONS[lang].get(key) or TRANSLATIONS["tr"].get(key, key)


def _clean_signature(data_url):
    """İmzayı doğrula; geçerliyse data URL'i, değilse None döndürür."""
    if not data_url:
        return None
    m = _SIG_RE.match(data_url.strip())
    if not m:
        return None
    raw = m.group(1)
    try:
        blob = base64.b64decode(raw, validate=False)
    except Exception:
        return None
    if not blob.startswith(b"\x89PNG\r\n\x1a\n") or len(blob) > MAX_SIG_BYTES:
        return None
    return "data:image/png;base64," + base64.b64encode(blob).decode("ascii")


@router.get("")
async def petition_page(request: Request):
    return templates.TemplateResponse(request, "petition.html", {
        "user": None,
        "i18n": _i18n(),
        "max_text": MAX_TEXT,
    })


@router.post("/pdf")
async def petition_pdf(request: Request,
                       text: str = Form(""),
                       signature: str = Form(""),
                       signer: str = Form(""),
                       place: str = Form(""),
                       lang: str = Form("tr")):
    body = (text or "").strip()
    if not body:
        return Response(_msg(lang, "pt_err_empty"), status_code=400,
                        media_type="text/plain; charset=utf-8")
    if len(body) > MAX_TEXT:
        return Response(_msg(lang, "pt_err_long"), status_code=400,
                        media_type="text/plain; charset=utf-8")

    sig = _clean_signature(signature)
    if not sig:
        return Response(_msg(lang, "pt_err_sig"), status_code=400,
                        media_type="text/plain; charset=utf-8")

    html_str = templates.get_template("petition_pdf.html").render(
        text=body,
        signature=sig,
        signer=(signer or "").strip()[:120],
        place=(place or "").strip()[:80],
        date_str=datetime.now().strftime("%d.%m.%Y"),
    )

    def _render():
        from weasyprint import HTML
        return HTML(string=html_str).write_pdf()

    try:
        import asyncio
        pdf = await asyncio.to_thread(_render)
    except Exception as e:
        return Response(f"PDF oluşturulamadı: {e}", status_code=500,
                        media_type="text/plain; charset=utf-8")

    fn = f"dilekce_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="{fn}"'})
