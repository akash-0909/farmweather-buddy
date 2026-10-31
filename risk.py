"""Transparent, rule-based rain-risk assessment. No AI is involved here.

The thresholds follow the India Meteorological Department (IMD) daily rainfall
categories: moderate rain starts at 15.6 mm/day and heavy rain at 64.5 mm/day.
Verify the numbers against the IMD page before you quote them in the pitch.
"""
from dataclasses import dataclass

MODERATE_RAIN_MM = 15.6
HEAVY_RAIN_MM = 64.5
WINDOW_DAYS = 3

# Version 1 is deliberately narrow: one crop, one hazard.
# heat_max_c: indicative daily max temperature above which the crop's sensitive
# stage can suffer heat stress. Rules of thumb, not official limits.
CROPS = {
    "Rice (paddy)": {"stage": "harvest and drying", "hazard": "heavy rain", "heat_max_c": 35.0},
    "Wheat": {"stage": "grain filling and harvest", "hazard": "heavy rain", "heat_max_c": 32.0},
    "Maize": {"stage": "harvest and drying", "hazard": "heavy rain", "heat_max_c": 35.0},
    "Cotton": {"stage": "boll opening and picking", "hazard": "heavy rain", "heat_max_c": 38.0},
    "Tomato": {"stage": "fruiting and picking", "hazard": "heavy rain", "heat_max_c": 35.0},
}


@dataclass
class RiskAssessment:
    level: str  # LOW | MEDIUM | HIGH | UNKNOWN
    window_days: int
    reason: str
    peak_date: str | None = None
    peak_mm: float | None = None
    peak_prob: int | None = None
    days_with_data: int = 0


def assess_rain_risk(days: list[dict], window: int = WINDOW_DAYS) -> RiskAssessment:
    """Classify the rain risk for the next `window` days from forecast rows."""
    win = days[:window]
    with_data = [d for d in win if d.get("precip_mm") is not None]

    if not with_data:
        return RiskAssessment(
            level="UNKNOWN",
            window_days=len(win),
            reason="The forecast contains no rainfall values for the next days, so risk cannot be judged.",
        )

    peak = max(with_data, key=lambda d: d["precip_mm"])
    mm = float(peak["precip_mm"])

    if mm >= HEAVY_RAIN_MM:
        level = "HIGH"
        reason = f"Forecast rainfall of {mm:.1f} mm on {peak['date']} reaches the heavy-rain level ({HEAVY_RAIN_MM} mm/day)."
    elif mm >= MODERATE_RAIN_MM:
        level = "MEDIUM"
        reason = f"Forecast rainfall of {mm:.1f} mm on {peak['date']} reaches the moderate-rain level ({MODERATE_RAIN_MM} mm/day)."
    else:
        level = "LOW"
        reason = f"The highest forecast rainfall in the next {len(win)} days is {mm:.1f} mm, below the moderate-rain level ({MODERATE_RAIN_MM} mm/day)."

    if len(with_data) < len(win):
        reason += f" Note: rainfall is missing for {len(win) - len(with_data)} of {len(win)} days, so this may be incomplete."

    return RiskAssessment(
        level=level,
        window_days=len(win),
        reason=reason,
        peak_date=peak["date"],
        peak_mm=mm,
        peak_prob=peak.get("precip_prob"),
        days_with_data=len(with_data),
    )
