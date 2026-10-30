"""Plain-language advice: an LLM explains the facts, with a rule-based fallback.

Providers (first key found wins): Gemini (free tier available), then Anthropic.
No key at all -> rule-based text.

Safeguards:
  1. The model only receives the computed facts and is told to use nothing else.
  2. Every number in the model's answer must appear in those facts, otherwise
     the answer is rejected and the rule-based text is shown instead.
  3. If there is no API key or the call fails, the rule-based text is used.
"""
import json
import re
from dataclasses import dataclass

from risk import RiskAssessment

DEFAULT_MODELS = {"gemini": "gemini-3.8-flash", "anthropic": "claude-haiku-5-5"}
DEFAULT_MODEL = DEFAULT_MODELS["anthropic"]  # kept for backward compatibility

SYSTEM_PROMPT = """You explain weather forecasts to farmers in simple, calm language.
Rules:
- Use ONLY the facts in the JSON the user sends. Do not invent numbers, dates, or conditions.
- Do not mention soil, market prices, satellite data, or pesticide/fertiliser doses.
- Write at most 110 words: first what the forecast says, then one cautious suggestion
  for the crop stage given. Use words like "consider" or "if possible".
- Use Western digits (0-9) for all numbers.
- End with one short sentence telling the farmer to confirm with their local agriculture office or KVK.
- Reply in the language requested in the JSON "language" field."""


@dataclass
class Advice:
    text: str
    method: str  # "ai" | "rules"
    note: str = ""


def build_facts(location: str, crop: str, crop_info: dict, assessment: RiskAssessment,
                days: list[dict], forecast_meta: dict, language: str) -> dict:
    return {
        "language": language,
        "location": location,
        "crop": crop,
        "crop_stage": crop_info["stage"],
        "hazard_checked": crop_info["hazard"],
        "risk_level": assessment.level,
        "risk_reason": assessment.reason,
        "peak_rain_date": assessment.peak_date,
        "peak_rain_mm": assessment.peak_mm,
        "peak_rain_probability_percent": assessment.peak_prob,
        "next_days": days[: assessment.window_days],
        "data_source": forecast_meta["source"],
        "retrieved_at_utc": forecast_meta["retrieved_at_utc"],
    }


def rule_based_advice(crop: str, crop_info: dict, a: RiskAssessment) -> str:
    stage = crop_info["stage"]
    if a.level == "HIGH":
        return (f"Heavy rain is forecast ({a.peak_mm:.1f} mm on {a.peak_date}). For {crop} at the {stage} stage, "
                "consider delaying harvest or drying work if possible, and protect cut or stored grain from getting wet. "
                "Please confirm with your local agriculture office or KVK.")
    if a.level == "MEDIUM":
        return (f"Moderate rain is forecast ({a.peak_mm:.1f} mm on {a.peak_date}). For {crop} at the {stage} stage, "
                "consider planning field work around the rainy day and keeping a cover ready for harvested grain. "
                "Please confirm with your local agriculture office or KVK.")
    if a.level == "LOW":
        return (f"No significant rain is forecast in the next {a.window_days} days (highest {a.peak_mm:.1f} mm). "
                f"Conditions look favourable for {stage} of {crop}, but forecasts can change, so check again before major work. "
                "Please confirm with your local agriculture office or KVK.")
    return "Rainfall data is unavailable, so no advice can be given right now. Please try again later or check local weather updates."


def _numbers(text: str) -> set[str]:
    return set(re.findall(r"[0-9]+(?:\.[0-9]+)?", text))


def _grounded(answer: str, facts: dict) -> bool:
    """True if every number in the answer is traceable to the facts (small counts 0-10 are allowed)."""
    allowed = _numbers(json.dumps(facts, ensure_ascii=False)) | {str(i) for i in range(0, 11)}
    # Accept "15" for "15.0" style differences.
    allowed |= {n.rstrip("0").rstrip(".") for n in allowed if "." in n}
    return all(n in allowed or n.rstrip("0").rstrip(".") in allowed for n in _numbers(answer))


def _call_gemini(facts: dict, api_key: str, model: str) -> str:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key, http_options=types.HttpOptions(timeout=20000))
    resp = client.models.generate_content(
        model=model,
        contents=json.dumps(facts, ensure_ascii=False),
        config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT, max_output_tokens=2048),
    )
    return (resp.text or "").strip()


def _call_anthropic(facts: dict, api_key: str, model: str) -> str:
    import anthropic

    client = anthropic.Anthropic(api_key=api_key, timeout=20.0, max_retries=1)
    msg = client.messages.create(
        model=model,
        max_tokens=400,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": json.dumps(facts, ensure_ascii=False)}],
    )
    return "".join(b.text for b in msg.content if getattr(b, "type", "") == "text").strip()


_CALLERS = {"gemini": _call_gemini, "anthropic": _call_anthropic}


def generate_advice(facts: dict, fallback_text: str, api_key: str | None = None,
                    model: str | None = None, provider: str = "anthropic") -> Advice:
    if facts["risk_level"] == "UNKNOWN":
        return Advice(fallback_text, "rules", "Rainfall data was missing, so no AI explanation was generated.")
    if not api_key or provider not in _CALLERS:
        return Advice(fallback_text, "rules", "No AI key configured; showing the rule-based explanation.")

    model = model or DEFAULT_MODELS[provider]
    try:
        text = _CALLERS[provider](facts, api_key, model)
    except Exception as exc:  # network, auth, quota, bad model name, etc.
        detail = str(exc).replace(api_key, "***")[:140]
        return Advice(fallback_text, "rules", f"AI service unavailable ({type(exc).__name__}: {detail}); showing the rule-based explanation.")

    if not text:
        return Advice(fallback_text, "rules", "AI returned an empty answer; showing the rule-based explanation.")
    if not text.endswith((".", "!", "?", "।", "。", "”", '"')):
        return Advice(fallback_text, "rules", "AI answer was cut off before finishing, so it was rejected; showing the rule-based explanation.")
    if not _grounded(text, facts):
        return Advice(fallback_text, "rules", "AI answer contained numbers not found in the forecast, so it was rejected; showing the rule-based explanation.")
    return Advice(text, "ai", f"Explained by {model} ({provider}) using only the forecast facts shown above.")