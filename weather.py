"""Live weather + geocoding via Open-Meteo (no API key needed)."""
import time
from datetime import datetime, timezone

import requests

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
SOURCE_NAME = "Open-Meteo Forecast API"
SOURCE_URL = "https://open-meteo.com/en/docs"


class DataUnavailable(Exception):
    """Raised when live data cannot be retrieved or is unusable."""


def _get(url: str, params: dict, retries: int = 2, timeout: int = 10) -> dict:
    last_error = None
    for attempt in range(retries + 1):
        try:
            resp = requests.get(url, params=params, timeout=timeout)
            resp.raise_for_status()
            return resp.json()
        except (requests.RequestException, ValueError) as exc:
            last_error = exc
            time.sleep(0.5 * (attempt + 1))
    raise DataUnavailable(f"Could not reach weather service: {last_error}")


def search_locations(name: str, count: int = 5) -> list[dict]:
    """Return candidate places for a free-text name (empty list if none)."""
    name = (name or "").strip()
    if len(name) < 2:
        return []
    data = _get(GEOCODE_URL, {"name": name, "count": count, "language": "en", "format": "json"})
    return data.get("results") or []


def get_forecast(lat: float, lon: float, days: int = 7) -> dict:
    """Fetch a daily forecast and stamp it with source + retrieval time."""
    data = _get(
        FORECAST_URL,
        {
            "latitude": lat,
            "longitude": lon,
            "daily": "precipitation_sum,precipitation_probability_max,temperature_2m_max,temperature_2m_min",
            "timezone": "auto",
            "forecast_days": days,
        },
    )
    daily = data.get("daily")
    if not daily or not daily.get("time"):
        raise DataUnavailable("The weather service returned no daily forecast for this location.")

    def col(key):
        values = daily.get(key) or [None] * len(daily["time"])
        return values

    rows = []
    for i, date in enumerate(daily["time"]):
        rows.append(
            {
                "date": date,
                "precip_mm": col("precipitation_sum")[i],
                "precip_prob": col("precipitation_probability_max")[i],
                "tmax": col("temperature_2m_max")[i],
                "tmin": col("temperature_2m_min")[i],
            }
        )
    return {
        "source": SOURCE_NAME,
        "source_url": SOURCE_URL,
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "timezone": data.get("timezone", "UTC"),
        "days": rows,
    }
