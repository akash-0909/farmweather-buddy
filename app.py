import os

import pandas as pd
import streamlit as st

import advisor
import risk
import weather

st.set_page_config(page_title="FarmWeather Buddy", page_icon="🌾", layout="centered")


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
        return "gemini", gemini_key, os.getenv("GEMINI_MODEL") or advisor.DEFAULT_MODELS["gemini"]
    claude_key = get_secret("ANTHROPIC_API_KEY")
    if claude_key:
        return "anthropic", claude_key, os.getenv("ANTHROPIC_MODEL") or advisor.DEFAULT_MODELS["anthropic"]
    return "anthropic", None, advisor.DEFAULT_MODELS["anthropic"]


def place_label(r: dict) -> str:
    parts = [r.get("name"), r.get("admin1"), r.get("country")]
    return ", ".join(p for p in parts if p)


st.title("🌾 FarmWeather Buddy")
st.caption("Live forecast → clear rain-risk check → plain-language advice. Forecast data only.")

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

    st.subheader(f"{crop_sel} · {name}")
    banner = {"LOW": st.success, "MEDIUM": st.warning, "HIGH": st.error, "UNKNOWN": st.info}[a.level]
    banner(f"**Rain risk (next {a.window_days} days): {a.level}**  \n{a.reason}")

    df = pd.DataFrame(fc["days"]).rename(
        columns={"date": "Date", "precip_mm": "Rain (mm)", "precip_prob": "Rain chance (%)", "tmax": "Max °C", "tmin": "Min °C"}
    )
    st.bar_chart(df.set_index("Date")["Rain (mm)"])
    st.dataframe(df, hide_index=True, use_container_width=True)

    facts = advisor.build_facts(name, crop_sel, crop_info, a, fc["days"], fc, lang)
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
        f"Times in {fc['timezone']}. This app uses rainfall and temperature forecasts only (no soil, market or satellite data). "
        "Forecasts can change; confirm with your local agriculture office."
    )
