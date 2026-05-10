"""Unit tests for src/metrics.py using a tiny inline DataFrame."""

import pandas as pd
import pytest

from metrics import aggregate_by, compare_weeks, detect_burning_creatives


def make_df() -> pd.DataFrame:
    """Two-week, two-campaign fixture.

    CampaignA — healthy (improves slightly week-over-week).
    CampaignB — burning creative (CTR -43%, CPI +50% in week 2).
    """
    rows = [
        # ── Week 1: 2026-04-21 ────────────────────────────────────────────
        {
            "date": "2026-04-21", "campaign": "CampaignA",
            "country": "US", "ad_network": "meta",
            "installs": 100, "clicks": 1_000, "impressions": 10_000,
            "cost": 200.0, "revenue_d1": 50.0, "revenue_d7": 150.0,
            "retention_d1": 0.30, "retention_d7": 0.12,
        },
        {
            "date": "2026-04-21", "campaign": "CampaignB",
            "country": "CA", "ad_network": "tiktok",
            "installs": 50, "clicks": 500, "impressions": 8_000,
            "cost": 300.0, "revenue_d1": 25.0, "revenue_d7": 80.0,
            "retention_d1": 0.28, "retention_d7": 0.10,
        },
        # ── Week 2: 2026-04-28 ────────────────────────────────────────────
        {
            "date": "2026-04-28", "campaign": "CampaignA",
            "country": "US", "ad_network": "meta",
            "installs": 110, "clicks": 1_100, "impressions": 11_000,
            "cost": 220.0, "revenue_d1": 55.0, "revenue_d7": 165.0,
            "retention_d1": 0.31, "retention_d7": 0.13,
        },
        {
            "date": "2026-04-28", "campaign": "CampaignB",
            "country": "CA", "ad_network": "tiktok",
            # CTR: 300/8500 = 3.5% vs 500/8000 = 6.25% → -43.5%  (threshold: >30%)
            # CPI: 360/40  = 9.0  vs 300/50  = 6.00  → +50%      (threshold: >20%)
            "installs": 40, "clicks": 300, "impressions": 8_500,
            "cost": 360.0, "revenue_d1": 18.0, "revenue_d7": 55.0,
            "retention_d1": 0.25, "retention_d7": 0.09,
        },
    ]
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    return df


# ── aggregate_by ─────────────────────────────────────────────────────────────

def test_aggregate_by_sums_cost_correctly():
    df = make_df()
    result = aggregate_by(df, group_by=["campaign"], week="2026-04-21")

    camp_a = result.loc[result["campaign"] == "CampaignA"].iloc[0]
    assert camp_a["cost"]     == 200.0
    assert camp_a["installs"] == 100

    camp_b = result.loc[result["campaign"] == "CampaignB"].iloc[0]
    assert camp_b["cost"]     == 300.0


def test_aggregate_by_derives_cpi():
    df = make_df()
    result = aggregate_by(df, group_by=["campaign"], week="2026-04-21")

    camp_a = result.loc[result["campaign"] == "CampaignA"].iloc[0]
    assert abs(camp_a["CPI"] - 2.0) < 0.001   # 200 / 100


# ── compare_weeks ────────────────────────────────────────────────────────────

def test_compare_weeks_totals():
    df = make_df()
    report = compare_weeks(df, current_week="2026-04-28", previous_week="2026-04-21")

    # Week 2 total: CampaignA 220 + CampaignB 360 = 580
    assert abs(report["totals"]["cost"] - 580.0) < 0.01
    # Week 2 installs: 110 + 40 = 150
    assert report["totals"]["installs"] == 150


def test_compare_weeks_cost_delta():
    df = make_df()
    report = compare_weeks(df, current_week="2026-04-28", previous_week="2026-04-21")

    # Week 1 total: 200 + 300 = 500; Week 2: 580 → delta = (580-500)/500 = 0.16
    assert abs(report["deltas"]["cost"] - 0.16) < 0.001


# ── detect_burning_creatives ─────────────────────────────────────────────────

def test_detect_burning_flags_campaign_b():
    df = make_df()
    burning = detect_burning_creatives(df)
    names = [b["campaign"] for b in burning]

    assert "CampaignB" in names


def test_detect_burning_does_not_flag_campaign_a():
    df = make_df()
    burning = detect_burning_creatives(df)
    names = [b["campaign"] for b in burning]

    # CampaignA's CTR and CPI are stable → should NOT appear
    assert "CampaignA" not in names


def test_detect_burning_returns_correct_direction():
    df = make_df()
    burning = detect_burning_creatives(df)
    b = next(x for x in burning if x["campaign"] == "CampaignB")

    assert b["CTR_change"] < -0.30   # CTR fell more than 30%
    assert b["CPI_change"] > 0.20    # CPI rose more than 20%
