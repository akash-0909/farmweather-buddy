import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import advisor  # noqa: E402
import risk  # noqa: E402


def day(date, mm, prob=50):
    return {"date": date, "precip_mm": mm, "precip_prob": prob, "tmax": 30, "tmin": 20}


def test_low_risk():
    a = risk.assess_rain_risk([day("2026-11-01", 1.0), day("2026-11-02", 3.0), day("2026-11-03", 0.0)])
    assert a.level == "LOW" and a.peak_mm == 3.0


def test_medium_risk_at_threshold():
    a = risk.assess_rain_risk([day("2026-11-01", 15.6), day("2026-11-02", 0), day("2026-11-03", 0)])
    assert a.level == "MEDIUM" and a.peak_date == "2026-11-01"


def test_high_risk():
    a = risk.assess_rain_risk([day("2026-11-01", 2), day("2026-11-02", 70.2), day("2026-11-03", 0)])
    assert a.level == "HIGH" and a.peak_date == "2026-11-02"


def test_only_window_days_count():
    days = [day("d1", 0), day("d2", 0), day("d3", 0), day("d4", 90)]
    assert risk.assess_rain_risk(days).level == "LOW"


def test_missing_data_is_unknown_not_low():
    days = [day("d1", None), day("d2", None), day("d3", None)]
    assert risk.assess_rain_risk(days).level == "UNKNOWN"


def test_partial_missing_data_is_flagged():
    a = risk.assess_rain_risk([day("d1", None), day("d2", 20), day("d3", 1)])
    assert a.level == "MEDIUM" and "missing" in a.reason


def _facts(a):
    meta = {"source": "Open-Meteo", "retrieved_at_utc": "2026-11-01T00:00:00+00:00"}
    info = risk.CROPS["Rice (paddy)"]
    days = [day("2026-11-01", 20.0, 80)]
    return advisor.build_facts("Ranchi, Jharkhand, India", "Rice (paddy)", info, a, days, meta, "English"), info


def test_no_key_falls_back_to_rules():
    a = risk.assess_rain_risk([day("2026-11-01", 20.0, 80)])
    facts, info = _facts(a)
    adv = advisor.generate_advice(facts, advisor.rule_based_advice("Rice (paddy)", info, a), api_key=None)
    assert adv.method == "rules" and "20.0" in adv.text


def test_unknown_never_calls_ai():
    a = risk.assess_rain_risk([day("d1", None)])
    facts, info = _facts(a)
    adv = advisor.generate_advice(facts, advisor.rule_based_advice("Rice (paddy)", info, a), api_key="fake")
    assert adv.method == "rules"


def test_grounding_accepts_known_numbers_and_rejects_invented_ones():
    a = risk.assess_rain_risk([day("2026-11-01", 20.0, 80)])
    facts, _ = _facts(a)
    assert advisor._grounded("About 20 mm of rain is likely on 2026-11-01, with an 80 percent chance.", facts)
    assert not advisor._grounded("Expect 120 mm of rain.", facts)
