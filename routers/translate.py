from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
import auth
from config import ANTHROPIC_API_KEY

router = APIRouter(prefix="/api")

LANG_NAMES = {"tr": "Turkish", "en": "English", "zh": "Simplified Chinese"}


class TranslateRequest(BaseModel):
    texts: dict          # {"name": "...", "description": "...", "specs": "..."}
    source_lang: str     # "tr" | "en" | "zh"
    target_langs: list   # ["tr", "en", "zh"] minus source


@router.post("/translate")
async def translate_texts(request: Request, body: TranslateRequest):
    auth.require_user(request)

    if not ANTHROPIC_API_KEY:
        return JSONResponse({"error": "ANTHROPIC_API_KEY sunucuda tanımlı değil."}, status_code=503)

    non_empty = {k: v for k, v in body.texts.items() if v and v.strip()}
    if not non_empty:
        return JSONResponse({"error": "Çevrilecek metin yok."}, status_code=400)

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

        results = {}
        for target in body.target_langs:
            if target == body.source_lang:
                continue
            src_name = LANG_NAMES.get(body.source_lang, body.source_lang)
            tgt_name = LANG_NAMES.get(target, target)

            lines = "\n".join(f"{k}: {v}" for k, v in non_empty.items())
            prompt = (
                f"Translate the following product/machine fields from {src_name} to {tgt_name}.\n"
                f"Return ONLY a JSON object with the same keys and translated values. No explanation.\n\n"
                f"{lines}"
            )

            msg = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )

            import json, re
            raw = msg.content[0].text.strip()
            # extract JSON block if wrapped in markdown
            m = re.search(r"\{[\s\S]*\}", raw)
            if m:
                raw = m.group(0)
            translated = json.loads(raw)
            results[target] = translated

        return JSONResponse({"ok": True, "translations": results})

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
