import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import planner  # noqa: E402
import risk  # noqa: E402
import weather  # noqa: E402


def d(mm=0.0, prob=10, wind=5.0, tmax=28.0, soil=0.25, et0=3.0, date="2026-11-01"):
    return {"date": date, "precip_mm": mm, "precip_prob": prob, "wind_kmh": wind, "tmax": tmax,
            "tmin": 18.0, "soil_moisture": soil, "et0_mm": et0}


def test_harvest_verdicts():
    assert planner.harvest_verdict(d(mm=0)) == planner.GOOD
    assert planner.harvest_verdict(d(mm=2)) == planner.CAUTION
    assert planner.harvest_verdict(d(mm=0, prob=80)) == planner.CAUTION
    assert planner.harvest_verdict(d(mm=8)) == planner.AVOID
    assert planner.harvest_verdict(d(mm=None)) == planner.UNKNOWN


def test_spray_verdicts():
    assert planner.spray_verdict(d()) == planner.GOOD
    assert planner.spray_verdict(d(wind=12)) == planner.CAUTION
    assert planner.spray_verdict(d(wind=20)) == planner.AVOID
    assert planner.spray_verdict(d(mm=3)) == planner.AVOID
    assert planner.spray_verdict(d(tmax=37)) == planner.CAUTION
    assert planner.spray_verdict(d(wind=None)) == planner.UNKNOWN


def test_irrigation_verdicts():
    assert planner.irrigate_verdict(d(mm=10)) == planner.SKIP
    assert planner.irrigate_verdict(d(soil=0.12)) == planner.NEEDED
    assert planner.irrigate_verdict(d(soil=0.35)) == planner.SKIP
    assert planner.irrigate_verdict(d(soil=0.25)) == planner.MONITOR


def test_irrigation_falls_back_to_et0_when_soil_missing():
    assert planner.irrigate_verdict(d(soil=None, et0=6.0, mm=0)) == planner.NEEDED
    assert planner.irrigate_verdict(d(soil=None, et0=2.0, mm=0)) == planner.MONITOR
    assert planner.irrigate_verdict(d(soil=None, et0=None, mm=None)) == planner.UNKNOWN


def test_heat_flag_is_crop_specific():
    hot = [d(tmax=33.5)]
    assert planner.build_plan(hot, risk.CROPS["Wheat"])[0].heat_stress is True
    assert planner.build_plan(hot, risk.CROPS["Cotton"])[0].heat_stress is False


def test_summary_lists_good_days():
    plan = planner.build_plan([d(date="2026-11-01"), d(mm=9, date="2026-11-02")], risk.CROPS["Rice (paddy)"])
    text = " ".join(planner.summarize(plan))
    assert "2026-11-01" in text and "Best harvest/drying days: 2026-11-01" in text


def test_every_crop_has_required_fields():
    for info in risk.CROPS.values():
        assert {"stage", "hazard", "heat_max_c"} <= set(info)


def test_daily_soil_moisture_averages_and_skips_missing():
    hourly = {"time": ["2026-11-01T00:00", "2026-11-01T01:00", "2026-11-02T00:00"],
              "soil_moisture_3_to_9cm": [0.2, 0.4, None]}
    assert weather.daily_soil_moisture(hourly) == {"2026-11-01": 0.3}
    assert weather.daily_soil_moisture(None) == {}
