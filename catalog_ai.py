"""AI-powered catalog content generator using Claude API."""

import json
import anthropic
from config import ANTHROPIC_API_KEY

_LANG_NAMES = {"tr": "Turkish", "en": "English", "zh": "Chinese (Simplified)"}

_SYSTEM = (
    "You are a senior industrial machinery catalog copywriter for a premium B2B brand. "
    "Write compelling, emotionally resonant marketing content that helps clients visualize "
    "the business value of each product. Use confident, professional tone. "
    "Respond ONLY with valid JSON, no markdown fences, no extra text."
)


def _build_prompt(model: dict, lang: str, specs: list, options: list) -> str:
    lang_name = _LANG_NAMES.get(lang, "Turkish")
    name = model.get(f"name_{lang}") or model.get("name") or ""
    desc = model.get(f"description_{lang}") or model.get("description") or ""
    spec_lines = "\n".join(
        f"- {s['title']}: {s.get('desc', '')}" for s in specs[:12] if s.get("title")
    )
    opt_entries = []
    for o in options[:12]:
        oname = o.get(f"name_{lang}") or o.get("name") or ""
        odesc = o.get(f"description_{lang}") or o.get("description") or ""
        if oname:
            opt_entries.append(f'  "{oname}": "{odesc}"')
    opt_block = "{\n" + ",\n".join(opt_entries) + "\n}" if opt_entries else "{}"
    opt_names_list = [o.get(f"name_{lang}") or o.get("name") or "" for o in options[:12] if o.get("name")]

    return f"""
Generate premium {lang_name} catalog content for this industrial machine:

Machine name: {name}
Description: {desc}
Specs:
{spec_lines or "(none)"}
Selected options/accessories (name → existing description):
{opt_block}

Return a single JSON object with EXACTLY these keys:

{{
  "headline": "One powerful marketing headline, max 10 words. No quotes inside.",
  "intro": "Rich 2-paragraph product introduction, 90-130 words total. Highlight productivity gains, precision, and ROI. Make the client feel this machine will transform their production.",
  "highlights": [
    "4-6 compelling selling points, each max 12 words. Focus on unique advantages."
  ],
  "specs_intro": "One sentence (max 18 words) leading into the specs table.",
  "cta": "One confident call-to-action sentence, max 15 words.",
  "option_benefits": [
    "3-5 sentences about the combined VALUE of having these specific options together. Focus on real business impact: time saved, quality gained, flexibility added. Write as a paragraph or separate list items."
  ],
  "option_texts": {{
    "OPTION_NAME_1": "2 sentences: first — what this option does, second — why it matters to the client's business.",
    "OPTION_NAME_2": "2 sentences: first — what this option does, second — why it matters."
  }}
}}

For option_texts, use the EXACT option names as keys: {opt_names_list}
If there are no options, use empty arrays/objects for option_benefits and option_texts.
Write ALL text values in {lang_name}. Be persuasive, confident, and specific.
""".strip()


def generate_catalog_content(model: dict, lang: str, specs: list, options: list) -> dict:
    """Call Claude to generate professional catalog text."""
    import logging
    log = logging.getLogger(__name__)

    if not ANTHROPIC_API_KEY:
        log.warning("ANTHROPIC_API_KEY not set — using fallback catalog content")
        fb = _fallback(model, lang, specs, options)
        fb["_debug"] = "no_api_key"
        return fb
    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=4096,
            system=_SYSTEM,
            messages=[{"role": "user", "content": _build_prompt(model, lang, specs, options)}],
        )
        raw = msg.content[0].text.strip()
        if raw.startswith("```"):
            parts = raw.split("```")
            raw = parts[1] if len(parts) > 1 else raw
            if raw.startswith("json"):
                raw = raw[4:]
        result = json.loads(raw.strip())
        ob = result.get("option_benefits", [])
        if isinstance(ob, str):
            result["option_benefits"] = [ob]
        result["_debug"] = "ai_ok"
        return result
    except Exception as e:
        log.error("Catalog AI generation failed: %s", e, exc_info=True)
        fb = _fallback(model, lang, specs, options)
        fb["_debug"] = f"error: {type(e).__name__}: {e}"
        return fb


def _fallback(model: dict, lang: str, specs: list, options: list) -> dict:
    name = model.get(f"name_{lang}") or model.get("name") or ""
    desc = model.get(f"description_{lang}") or model.get("description") or ""
    highlights = [s["title"] for s in specs[:5] if s.get("title")]
    suffix = {"tr": "ile tanışın.", "en": "— built for excellence.", "zh": "，品质卓越。"}.get(lang, ".")
    opt_texts = {}
    for o in options:
        oname = o.get(f"name_{lang}") or o.get("name") or ""
        odesc = o.get(f"description_{lang}") or o.get("description") or ""
        if oname:
            opt_texts[oname] = odesc
    return {
        "headline": f"{name}{suffix}",
        "intro": desc or name,
        "highlights": highlights,
        "specs_intro": {"tr": "Teknik özellikler aşağıda listelenmiştir.",
                        "en": "Technical specifications are listed below.",
                        "zh": "技术规格如下所列。"}.get(lang, ""),
        "cta": {"tr": "Detaylı bilgi ve teklif için bizimle iletişime geçin.",
                "en": "Contact us for detailed information and a quote.",
                "zh": "请联系我们获取详细信息和报价。"}.get(lang, ""),
        "option_benefits": [],
        "option_texts": opt_texts,
    }
