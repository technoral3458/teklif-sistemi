"""AI-powered catalog content generator using Claude API."""

import json
import anthropic
from config import ANTHROPIC_API_KEY

_LANG_NAMES = {"tr": "Turkish", "en": "English", "zh": "Chinese (Simplified)"}

_SYSTEM = (
    "You are a professional industrial machinery catalog copywriter. "
    "Write compelling, precise marketing content for B2B machine catalogs. "
    "Keep technical accuracy while using persuasive business language. "
    "Respond ONLY with valid JSON, no extra text."
)


def _build_prompt(model: dict, lang: str, specs: list, options: list) -> str:
    lang_name = _LANG_NAMES.get(lang, "Turkish")
    name = (
        model.get(f"name_{lang}") or model.get("name") or ""
    )
    desc = (
        model.get(f"description_{lang}") or model.get("description") or ""
    )
    spec_lines = "\n".join(
        f"- {s['title']}: {s.get('desc','')}" for s in specs if s.get("title")
    )
    opt_names = ", ".join(o.get("name", "") for o in options[:10] if o.get("name"))

    return f"""
Generate professional {lang_name} catalog content for the following industrial machine.

Machine name: {name}
Existing description: {desc}
Technical specifications:
{spec_lines or "(none provided)"}
Available options/accessories: {opt_names or "(none)"}

Return JSON with exactly these keys:
{{
  "headline": "One-line marketing headline (max 12 words)",
  "intro": "Professional 2-paragraph introduction (80-120 words total). Focus on productivity, quality, and business value.",
  "highlights": ["Selling point 1", "Selling point 2", "Selling point 3", "Selling point 4"],
  "specs_intro": "One sentence introducing the technical specifications table (max 20 words).",
  "cta": "Short call-to-action sentence (max 15 words)."
}}

Write everything in {lang_name}. Be concise and professional.
""".strip()


def generate_catalog_content(model: dict, lang: str, specs: list, options: list) -> dict:
    """Call Claude to generate professional catalog text. Returns dict with content keys."""
    if not ANTHROPIC_API_KEY:
        return _fallback(model, lang, specs)
    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=_SYSTEM,
            messages=[{"role": "user", "content": _build_prompt(model, lang, specs, options)}],
        )
        raw = msg.content[0].text.strip()
        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw.strip())
    except Exception:
        return _fallback(model, lang, specs)


def _fallback(model: dict, lang: str, specs: list) -> dict:
    """Return model's existing content when AI is unavailable."""
    name = model.get(f"name_{lang}") or model.get("name") or ""
    desc = model.get(f"description_{lang}") or model.get("description") or ""
    highlights = [s["title"] for s in specs[:4] if s.get("title")]
    suffix = {"tr": "ile tanışın.", "en": "— built for excellence.", "zh": "，品质卓越。"}.get(lang, ".")
    return {
        "headline": f"{name}{suffix}",
        "intro": desc or name,
        "highlights": highlights,
        "specs_intro": {
            "tr": "Teknik özellikler aşağıda listelenmiştir.",
            "en": "Technical specifications are listed below.",
            "zh": "技术规格如下所列。",
        }.get(lang, ""),
        "cta": {
            "tr": "Detaylı bilgi ve fiyat teklifi için bizimle iletişime geçin.",
            "en": "Contact us for detailed information and a price quote.",
            "zh": "请联系我们获取详细信息和报价。",
        }.get(lang, ""),
    }
