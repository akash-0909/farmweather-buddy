import os

import pandas as pd
import streamlit as st

import advisor
import planner
import risk
import weather

st.set_page_config(page_title="FarmWeather Buddy", page_icon="🌾", layout="centered")

BADGE = {
    planner.GOOD: "✅ Good", planner.CAUTION: "⚠️ Caution", planner.AVOID: "❌ Avoid", planner.UNKNOWN: "❓ No data",
    planner.NEEDED: "💧 Needed", planner.MONITOR: "👀 Monitor", planner.SKIP: "⏭️ Skip",
}


@st.cache_data(ttl=600, show_spinner=False)
def cached_search(query: str):
    return weather.search_locations(query)


@st.cache_data(ttl=600, show_spinner=False)
def cached_forecast(lat: float, lon: float):
    return weather.get_forecast(lat, lon)


def get_secret(name: str):
    value = os.getenv(name)
    if value:
        return value
    try:
        return st.secrets.get(name)
    except Exception:
        return None


def get_llm_config():
    """Gemini first (free tier), then Anthropic. Returns (provider, api_key, model)."""
    gemini_key = get_secret("GEMINI_API_KEY")
    if gemini_key:
        return "gemini", gemini_key, get_secret("GEMINI_MODEL") or advisor.DEFAULT_MODELS["gemini"]
    claude_key = get_secret("ANTHROPIC_API_KEY")
    if claude_key:
        return "anthropic", claude_key, get_secret("ANTHROPIC_MODEL") or advisor.DEFAULT_MODELS["anthropic"]
    return "anthropic", None, advisor.DEFAULT_MODELS["anthropic"]


def place_label(r: dict) -> str:
    parts = [r.get("name"), r.get("admin1"), r.get("country")]
    return ", ".join(p for p in parts if p)


st.title("🌾 FarmWeather Buddy")
st.caption("Live forecast → rain-risk check → 7-day farm activity plan → plain-language advice.")

col1, col2 = st.columns(2)
with col1:
    query = st.text_input("Village / town", value="Ranchi")
with col2:
    crop = st.selectbox("Crop", list(risk.CROPS.keys()))
language = st.radio("Advice language", ["English", "Hindi"], horizontal=True)

try:
    places = cached_search(query)
except weather.DataUnavailable as exc:
    places = []
    st.error(f"Location search is unavailable right now. {exc}")

if query.strip() and not places:
    st.warning("No matching place found. Try a nearby town or check the spelling.")

place = None
if places:
    labels = [place_label(p) for p in places]
    choice = st.selectbox("Select the exact place", labels)
    place = places[labels.index(choice)]

if st.button("Check forecast", type="primary", disabled=place is None):
    st.session_state["run"] = (place["latitude"], place["longitude"], place_label(place), crop, language)

run = st.session_state.get("run")
if run:
    lat, lon, name, crop_sel, lang = run
    crop_info = risk.CROPS[crop_sel]

    try:
        with st.spinner("Fetching live forecast…"):
            fc = cached_forecast(lat, lon)
    except weather.DataUnavailable as exc:
        st.error(f"Could not get live forecast data, so no advice is shown. {exc}")
        st.stop()

    a = risk.assess_rain_risk(fc["days"])
    day_plan = planner.build_plan(fc["days"], crop_info)

    st.subheader(f"{crop_sel} · {name}")
    banner = {"LOW": st.success, "MEDIUM": st.warning, "HIGH": st.error, "UNKNOWN": st.info}[a.level]
    banner(f"**Rain risk (next {a.window_days} days): {a.level}**  \n{a.reason}")

    tab_plan, tab_data = st.tabs(["📅 7-day activity plan", "📊 Forecast data"])

    with tab_plan:
        plan_df = pd.DataFrame(
            [
                {
                    "Date": p.date,
                    "Harvest / dry": BADGE[p.harvest],
                    "Spray": BADGE[p.spray],
                    "Irrigate": BADGE[p.irrigate],
                    "Why": ", ".join(p.reasons) or "calm day",
                }
                for p in day_plan
            ]
        )
        st.dataframe(plan_df, hide_index=True, use_container_width=True)
        for line in planner.summarize(day_plan):
            st.write("• " + line)
        t = planner.THRESHOLDS
        with st.expander("How these verdicts are decided"):
            st.markdown(
                f"- **Harvest/dry:** avoid if rain ≥ {t['harvest_avoid_mm']} mm; caution if rain ≥ {t['harvest_caution_mm']} mm or chance ≥ {t['rain_prob_caution']}%.\n"
                f"- **Spray:** avoid if rain ≥ {t['spray_avoid_mm']} mm or wind ≥ {t['spray_avoid_wind_kmh']} km/h; caution for wind ≥ {t['spray_caution_wind_kmh']} km/h, high rain chance, or heat ≥ {t['spray_hot_c']} °C.\n"
                f"- **Irrigate:** skip if rain ≥ {t['irrigate_skip_mm']} mm; needed if topsoil moisture (3–9 cm) is below {t['soil_dry']} m³/m³; otherwise monitor.\n"
                f"- **Heat stress** flag uses a crop-specific limit ({crop_info['heat_max_c']} °C for {crop_sel}).\n\n"
                "These are indicative rules of thumb, not official standards. Soil moisture is a model estimate for the area, not a field sensor reading."
            )

    with tab_data:
        df = pd.DataFrame(fc["days"]).rename(
            columns={
                "date": "Date", "precip_mm": "Rain (mm)", "precip_prob": "Rain chance (%)", "tmax": "Max °C",
                "tmin": "Min °C", "wind_kmh": "Wind (km/h)", "et0_mm": "ET₀ (mm)", "soil_moisture": "Soil moisture (m³/m³)",
            }
        )
        st.bar_chart(df.set_index("Date")["Rain (mm)"])
        st.dataframe(df, hide_index=True, use_container_width=True)

    facts = advisor.build_facts(name, crop_sel, crop_info, a, fc["days"], fc, lang, planner.plan_to_facts(day_plan))
    fallback = advisor.rule_based_advice(crop_sel, crop_info, a)
    with st.spinner("Writing advice…"):
        provider, api_key, model = get_llm_config()
        advice = advisor.generate_advice(facts, fallback, api_key, model, provider)

    st.subheader("What this means for you")
    st.write(advice.text)
    if lang == "Hindi" and advice.method == "rules":
        st.caption("Hindi needs the AI service; showing English because it is unavailable.")
    st.caption(advice.note)

    st.divider()
    st.caption(
        f"Source: [{fc['source']}]({fc['source_url']}) · Retrieved {fc['retrieved_at_utc']} UTC · "
        f"Times in {fc['timezone']}. Data used: rainfall, temperature, wind, evapotranspiration and modelled soil moisture forecasts "
        "(no market or satellite-imagery data). Forecasts can change; confirm with your local agriculture office."
    )
