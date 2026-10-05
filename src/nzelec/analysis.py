"""The analysis itself: pure functions from the tidy daily table to summary tables."""

from __future__ import annotations

import pandas as pd

from .load import GROUP_ORDER


def monthly_by_group(daily: pd.DataFrame) -> pd.DataFrame:
    """GWh per month (rows) by fuel group (columns), in fixed group order."""
    out = (
        daily.assign(month=daily["date"].dt.to_period("M").dt.to_timestamp())
        .pivot_table(index="month", columns="group", values="gwh", aggfunc="sum", fill_value=0)
    )
    return out.reindex(columns=[g for g in GROUP_ORDER if g in out.columns])


def renewable_share(daily: pd.DataFrame, freq: str = "M") -> pd.DataFrame:
    """Renewable share of generation per period. freq: 'M' monthly or 'Y' yearly."""
    period = daily["date"].dt.to_period(freq).dt.to_timestamp()
    g = daily.groupby([period, "renewable"])["gwh"].sum().unstack(fill_value=0)
    g = g.reindex(columns=[True, False], fill_value=0)
    total = g.sum(axis=1)
    out = pd.DataFrame(
        {
            "renewable_gwh": g[True],
            "total_gwh": total,
            "renewable_pct": 100 * g[True] / total,
        }
    )
    out.index.name = "period"
    return out


def rolling_12m_share(monthly_share: pd.DataFrame) -> pd.Series:
    """12-month rolling renewable share - smooths out the seasonal hydro cycle."""
    r = monthly_share["renewable_gwh"].rolling(12).sum()
    t = monthly_share["total_gwh"].rolling(12).sum()
    return (100 * r / t).rename("renewable_pct_12m")


def seasonal_profile(daily: pd.DataFrame) -> pd.DataFrame:
    """Average share of each fuel group by calendar month (Jan..Dec), across all years."""
    m = monthly_by_group(daily)
    share = m.div(m.sum(axis=1), axis=0) * 100
    return share.groupby(share.index.month).mean().rename_axis("calendar_month")


def daily_shape(half_hourly: pd.DataFrame) -> pd.DataFrame:
    """Average MW by fuel group for each half-hour of the day.

    kWh in a half hour / 0.5 h = average kW; /1000 -> MW. Divided by the number
    of days so the result is a typical day.
    """
    n_days = half_hourly.attrs.get("n_days", 1)
    prof = half_hourly.pivot_table(index="tp", columns="group", values="kwh", aggfunc="sum", fill_value=0)
    prof = prof / n_days / 0.5 / 1000
    return prof.reindex(columns=[g for g in GROUP_ORDER if g in prof.columns])


def headline_findings(daily: pd.DataFrame) -> dict:
    """A few numbers worth quoting in the README."""
    yearly = renewable_share(daily, "Y")
    monthly = renewable_share(daily, "M")
    by_group = daily.groupby("group")["gwh"].sum()
    best = monthly["renewable_pct"].idxmax()
    worst = monthly["renewable_pct"].idxmin()
    return {
        "period": f"{daily['date'].min():%b %Y} – {daily['date'].max():%b %Y}",
        "total_twh": round(daily["gwh"].sum() / 1000, 1),
        "renewable_pct_overall": round(100 * daily.loc[daily["renewable"], "gwh"].sum() / daily["gwh"].sum(), 1),
        "renewable_pct_by_year": yearly["renewable_pct"].round(1).set_axis(yearly.index.year).to_dict(),
        "best_month": (f"{best:%b %Y}", round(monthly.loc[best, "renewable_pct"], 1)),
        "worst_month": (f"{worst:%b %Y}", round(monthly.loc[worst, "renewable_pct"], 1)),
        "largest_source": by_group.idxmax(),
        "largest_source_pct": round(100 * by_group.max() / by_group.sum(), 1),
    }
