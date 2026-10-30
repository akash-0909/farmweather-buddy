# 🌾 FarmWeather Buddy

Forge '26 · Theme 2 (Climate, Agriculture, and Supply Resilience)

Pick a place and a crop. The app fetches a **live forecast** from Open-Meteo, applies a **transparent rain-risk rule**, and uses **Gen AI** to explain the result in simple English or Hindi with one cautious suggestion. It always shows the data source and retrieval time, and says so when data is unavailable.

## How it works

```
User input (place, crop)
   │
   ▼
weather.py  ── Open-Meteo Geocoding + Forecast APIs (live, retried, time-stamped)
   │
   ▼
risk.py     ── rule-based LOW / MEDIUM / HIGH / UNKNOWN (IMD rainfall categories)
   │
   ▼
advisor.py  ── LLM explains only the computed facts
   │            ├─ number-grounding check (reject answers with invented numbers)
   │            └─ rule-based fallback if no key / API error / rejected answer
   ▼
app.py      ── Streamlit UI: risk banner, chart, table, advice, source + time
```

## Scope (version 1)

- One crop: Rice (paddy), harvest and drying stage
- One hazard: rain in the next 3 days
- Data used: rainfall and temperature forecast only. **No soil, market, or satellite data is used or claimed.**

## Run locally

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
export GEMINI_API_KEY="your-key"                    # free key from Google AI Studio (recommended)
# or: export ANTHROPIC_API_KEY="your-key"           # paid alternative
streamlit run app.py
```

With no key the app still works and shows the rule-based explanation. If both keys are set, Gemini is used.
Optional model overrides: `GEMINI_MODEL`, `ANTHROPIC_MODEL`. Check the model name in the Gemini docs, as names change.

## Test

```bash
pip install pytest
pytest -q
```

## Deploy (Streamlit Community Cloud)

1. Push this folder to a public GitHub repo.
2. On share.streamlit.io choose the repo and `app.py`.
3. In **Advanced settings → Secrets** add: `GEMINI_API_KEY = "your-key"`
4. Open the public URL and test it before submitting.

## Safeguards and edge cases

| Situation | Behaviour |
|---|---|
| Weather API unreachable | Retries, then shows an error and **no advice** (nothing is made up) |
| Place not found / empty input | Clear warning, button disabled |
| Rainfall values missing | Risk shown as UNKNOWN, never as LOW |
| Some days missing | Risk computed from available days and flagged as possibly incomplete |
| LLM missing, failing, or empty | Rule-based explanation, labelled as such |
| LLM mentions a number not in the forecast | Answer rejected, rule-based explanation shown |

## Data sources

- [Open-Meteo Forecast API](https://open-meteo.com/en/docs) and Geocoding API (no key required)
- Rain thresholds: IMD daily rainfall categories (moderate ≥ 15.6 mm, heavy ≥ 64.5 mm)

## Limitations

Forecasts can be wrong and are not a substitute for local agriculture advice (KVK). Version 1 covers one crop and one hazard by design.
