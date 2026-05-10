"""Load campaign data and compute UA metrics."""

from __future__ import annotations

import pandas as pd


REQUIRED_COLUMNS = [
    "date", "campaign", "country", "ad_network",
    "installs", "clicks", "impressions", "cost",
    "revenue_d1", "revenue_d7", "retention_d1", "retention_d7",
]


def load_campaigns(path: str) -> pd.DataFrame:
    """Read the CSV, parse dates, and validate required columns."""
    df = pd.read_csv(path, parse_dates=["date"])
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"CSV is missing columns: {missing}")
    return df


def _week_slice(df: pd.DataFrame, week: str) -> pd.DataFrame:
    """Return rows whose date falls in the 7-day window starting on `week` (YYYY-MM-DD)."""
    start = pd.Timestamp(week)
    end = start + pd.Timedelta(days=6)
    return df[(df["date"] >= start) & (df["date"] <= end)]


def aggregate_by(
    df: pd.DataFrame,
    group_by: list[str],
    week: str | None = None,
) -> pd.DataFrame:
    """Group and sum raw metrics, then derive CPI, ROAS_d7, CTR, CVR.

    Args:
        df:       Full campaigns DataFrame.
        group_by: Columns to group by (e.g. ["campaign"] or ["campaign", "country"]).
        week:     If given, only include the 7 days starting on this date (YYYY-MM-DD).
    """
    if week:
        df = _week_slice(df, week)

    grouped = (
        df.groupby(group_by, as_index=False)
        .agg(
            cost=("cost", "sum"),
            installs=("installs", "sum"),
            clicks=("clicks", "sum"),
            impressions=("impressions", "sum"),
            revenue_d1=("revenue_d1", "sum"),
            revenue_d7=("revenue_d7", "sum"),
        )
    )

    # Avoid division by zero — missing values stay as NaN
    grouped["CPI"]     = grouped["cost"]     / grouped["installs"].replace(0, float("nan"))
    grouped["ROAS_d7"] = grouped["revenue_d7"] / grouped["cost"].replace(0, float("nan"))
    grouped["CTR"]     = grouped["clicks"]   / grouped["impressions"].replace(0, float("nan"))
    grouped["CVR"]     = grouped["installs"] / grouped["clicks"].replace(0, float("nan"))

    return grouped


def compare_weeks(
    df: pd.DataFrame,
    current_week: str,
    previous_week: str,
) -> dict:
    """Return top-line totals and week-over-week deltas for both weeks.

    Returns a dict with two keys:
      "totals" — absolute values for the current week.
      "deltas" — fractional change vs previous week (0.10 = +10%).
    """
    def _totals(week: str) -> dict:
        sub = _week_slice(df, week)
        cost        = sub["cost"].sum()
        installs    = sub["installs"].sum()
        clicks      = sub["clicks"].sum()
        impressions = sub["impressions"].sum()
        revenue_d7  = sub["revenue_d7"].sum()
        return {
            "cost":       cost,
            "installs":   installs,
            "revenue_d7": revenue_d7,
            "CPI":        cost / installs   if installs    else 0.0,
            "ROAS_d7":    revenue_d7 / cost if cost        else 0.0,
            "CTR":        clicks / impressions if impressions else 0.0,
        }

    current  = _totals(current_week)
    previous = _totals(previous_week)

    deltas = {
        key: (current[key] - previous[key]) / previous[key] if previous[key] else 0.0
        for key in current
    }

    return {"totals": current, "deltas": deltas}


def detect_burning_creatives(df: pd.DataFrame) -> list[dict]:
    """Find campaigns where CTR fell >30% AND CPI rose >20% week-over-week.

    Compares the two most recent full weeks inferred from the data's date range.
    Returns a list of dicts with campaign name, before/after CTR and CPI, and % changes.
    """
    latest = df["date"].max()
    # The last date in the file is the end of week 2; walk back to find both week starts.
    current_week_start = (latest - pd.Timedelta(days=6)).strftime("%Y-%m-%d")
    prev_week_start    = (latest - pd.Timedelta(days=13)).strftime("%Y-%m-%d")

    curr = aggregate_by(df, group_by=["campaign"], week=current_week_start)
    prev = aggregate_by(df, group_by=["campaign"], week=prev_week_start)

    merged = curr.merge(prev, on="campaign", suffixes=("_curr", "_prev"))

    results = []
    for _, row in merged.iterrows():
        if row["CTR_prev"] == 0 or row["CPI_prev"] == 0:
            continue
        ctr_change = (row["CTR_curr"] - row["CTR_prev"]) / row["CTR_prev"]
        cpi_change = (row["CPI_curr"] - row["CPI_prev"]) / row["CPI_prev"]

        if ctr_change < -0.30 and cpi_change > 0.20:
            results.append({
                "campaign":   row["campaign"],
                "CTR_prev":   row["CTR_prev"],
                "CTR_curr":   row["CTR_curr"],
                "CTR_change": ctr_change,
                "CPI_prev":   row["CPI_prev"],
                "CPI_curr":   row["CPI_curr"],
                "CPI_change": cpi_change,
            })

    return results


def top_n_by(
    df: pd.DataFrame,
    metric: str,
    n: int = 3,
    ascending: bool = False,
) -> pd.DataFrame:
    """Return the top `n` rows sorted by `metric`."""
    return df.sort_values(metric, ascending=ascending).head(n)
