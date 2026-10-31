"""7-day farm activity planner: transparent rules, no AI.

IMPORTANT: the thresholds below are indicative rules of thumb, not official
standards. They are kept in one place (THRESHOLDS) so they can be tuned with a
local agronomist. The app shows them to the user.
"""
from dataclasses import dataclass

THRESHOLDS = {
    "harvest_avoid_mm": 5.0,      # rain at/above this: avoid harvesting and drying
    "harvest_caution_mm": 1.0,
    "rain_prob_caution": 60,      # percent
    "spray_avoid_mm": 2.0,        # rain washes spray off
    "spray_avoid_wind_kmh": 15.0, # drift risk
    "spray_caution_wind_kmh": 10.0,
    "spray_hot_c": 35.0,          # hot day: spray evaporates quickly
    "irrigate_skip_mm": 5.0,      # enough rain to skip irrigation
    "soil_dry": 0.20,             # m3/m3, generic; depends on soil type
    "soil_moist": 0.30,
    "et0_deficit_mm": 4.0,        # fallback when soil moisture is missing
}

GOOD, CAUTION, AVOID, UNKNOWN = "GOOD", "CAUTION", "AVOID", "UNKNOWN"
NEEDED, MONITOR, SKIP = "NEEDED", "MONITOR", "SKIP"


@dataclass
class DayPlan:
    date: str
    harvest: str
    spray: str
    irrigate: str
    heat_stress: bool
    reasons: list[str]


def _has(*values) -> bool:
    return all(v is not None for v in values)


def harvest_verdict(d: dict) -> str:
    mm, prob = d.get("precip_mm"), d.get("precip_prob")
    if mm is None:
        return UNKNOWN
    if mm >= THRESHOLDS["harvest_avoid_mm"]:
        return AVOID
    if mm >= THRESHOLDS["harvest_caution_mm"] or (prob is not None and prob >= THRESHOLDS["rain_prob_caution"]):
        return CAUTION
    return GOOD


def spray_verdict(d: dict) -> str:
    mm, wind, prob, tmax = d.get("precip_mm"), d.get("wind_kmh"), d.get("precip_prob"), d.get("tmax")
    if not _has(mm, wind):
        return UNKNOWN
    if mm >= THRESHOLDS["spray_avoid_mm"] or wind >= THRESHOLDS["spray_avoid_wind_kmh"]:
        return AVOID
    if (
        wind >= THRESHOLDS["spray_caution_wind_kmh"]
        or (prob is not None and prob >= THRESHOLDS["rain_prob_caution"])
        or (tmax is not None and tmax >= THRESHOLDS["spray_hot_c"])
    ):
        return CAUTION
    return GOOD


def irrigate_verdict(d: dict) -> str:
    mm, soil, et0 = d.get("precip_mm"), d.get("soil_moisture"), d.get("et0_mm")
    if mm is not None and mm >= THRESHOLDS["irrigate_skip_mm"]:
        return SKIP
    if soil is not None:
        if soil < THRESHOLDS["soil_dry"] and (mm is None or mm < 2):
            return NEEDED
        if soil >= THRESHOLDS["soil_moist"]:
            return SKIP
        return MONITOR
    if _has(mm, et0):
        return NEEDED if et0 - mm >= THRESHOLDS["et0_deficit_mm"] else MONITOR
    return UNKNOWN


def build_plan(days: list[dict], crop_info: dict) -> list[DayPlan]:
    heat_limit = crop_info.get("heat_max_c")
    plan = []
    for d in days:
        reasons = []
        harvest, spray, irrigate = harvest_verdict(d), spray_verdict(d), irrigate_verdict(d)
        tmax = d.get("tmax")
        heat = bool(heat_limit is not None and tmax is not None and tmax >= heat_limit)
        if d.get("precip_mm") is not None and d["precip_mm"] >= THRESHOLDS["harvest_caution_mm"]:
            reasons.append(f"rain {d['precip_mm']:.1f} mm")
        if d.get("wind_kmh") is not None and d["wind_kmh"] >= THRESHOLDS["spray_caution_wind_kmh"]:
            reasons.append(f"wind {d['wind_kmh']:.0f} km/h")
        if heat:
            reasons.append(f"heat {tmax:.1f} °C")
        plan.append(DayPlan(d["date"], harvest, spray, irrigate, heat, reasons))
    return plan


def plan_to_facts(plan: list[DayPlan]) -> list[dict]:
    return [
        {"date": p.date, "harvest": p.harvest, "spray": p.spray, "irrigate": p.irrigate, "heat_stress": p.heat_stress}
        for p in plan
    ]


def summarize(plan: list[DayPlan]) -> list[str]:
    """Computed (not AI) one-line summaries of the best days."""
    out = []
    harvest = [p.date for p in plan if p.harvest == GOOD]
    spray = [p.date for p in plan if p.spray == GOOD]
    irrigate = [p.date for p in plan if p.irrigate == NEEDED]
    heat = [p.date for p in plan if p.heat_stress]
    out.append("Best harvest/drying days: " + (", ".join(harvest) if harvest else "none in the next 7 days"))
    out.append("Best spraying days: " + (", ".join(spray) if spray else "none in the next 7 days"))
    out.append("Irrigation likely needed: " + (", ".join(irrigate) if irrigate else "no day flagged"))
    if heat:
        out.append("Heat stress risk for this crop: " + ", ".join(heat))
    return out
