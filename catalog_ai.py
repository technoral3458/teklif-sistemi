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
    for o in options:
        oname = o.get(f"name_{lang}") or o.get("name") or ""
        odesc = o.get(f"description_{lang}") or o.get("description") or ""
        if oname:
            opt_entries.append(f'  "{oname}": "{odesc}"')
    opt_block = "{\n" + ",\n".join(opt_entries) + "\n}" if opt_entries else "{}"
    opt_names_list = [o.get(f"name_{lang}") or o.get("name") or "" for o in options if o.get("name")]

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
    "OPTION_NAME_1": "One punchy sentence: what it does AND why it matters to production.",
    "OPTION_NAME_2": "One punchy sentence: what it does AND why it matters to production."
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


def generate_general_catalog_content(models: list, lang: str, company_name: str) -> dict:
    """Generate company-level catalog intro + tagline per model + spec descriptions."""
    import logging
    log = logging.getLogger(__name__)

    lang_name = _LANG_NAMES.get(lang, "Turkish")
    if not ANTHROPIC_API_KEY:
        return _general_fallback(models, lang)
    try:
        model_entries = []
        for m in models[:12]:
            name = m.get(f"name_{lang}") or m.get("name", "")
            cat = m.get("_cat_name", "")
            desc = (m.get(f"description_{lang}") or m.get("description", ""))[:80]
            specs = m.get("_specs", [])[:8]
            spec_parts = "; ".join(
                f'{s["title"]}: {(s.get(f"desc_{lang}") or s.get("desc",""))[:50]}'
                for s in specs if s.get("title")
            )
            model_entries.append(
                f'- "{name}" [{cat}]: {desc}. Specs: {spec_parts or "none"}'
            )
        model_lines = "\n".join(model_entries)

        # Build example spec structure for the prompt
        spec_example_model = ""
        spec_example_keys = ""
        for m in models[:1]:
            spec_example_model = m.get(f"name_{lang}") or m.get("name", "")
            specs = m.get("_specs", [])[:2]
            spec_example_keys = ", ".join(f'"{s["title"]}"' for s in specs if s.get("title"))

        prompt = f"""You are writing a premium B2B industrial machinery catalog for "{company_name}".

Models with specs:
{model_lines}

Return a single JSON object:
{{
  "catalog_intro": "2 sentences (max 50 words) introducing the company catalog. Focus on quality, range, and business value.",
  "model_taglines": {{
    "EXACT_MODEL_NAME": "One punchy tagline (max 12 words) for this machine.",
    ...
  }},
  "model_spec_texts": {{
    "EXACT_MODEL_NAME": {{
      "EXACT_SPEC_TITLE": "One concise sentence (max 15 words) on the business value of this spec for the customer.",
      ...
    }},
    ...
  }}
}}

Use EXACT model names and spec titles as keys. Write everything in {lang_name}. Be confident and specific.
""".strip()

        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=4096,
            system=_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = msg.content[0].text.strip()
        if raw.startswith("```"):
            parts = raw.split("```")
            raw = parts[1] if len(parts) > 1 else raw
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw.strip())
    except Exception as e:
        log.error("General catalog AI failed: %s", e, exc_info=True)
        return _general_fallback(models, lang)


def _general_fallback(models: list, lang: str) -> dict:
    taglines = {}
    for m in models:
        name = m.get(f"name_{lang}") or m.get("name") or ""
        desc = m.get(f"description_{lang}") or m.get("description") or ""
        taglines[name] = desc[:80] if desc else name
    return {"catalog_intro": "", "model_taglines": taglines, "model_spec_texts": {}}


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
