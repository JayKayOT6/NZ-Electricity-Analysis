"""Download NZ generation data, run the analysis, write tables + charts.

Usage:
    python run_analysis.py                          # last full 3 years
    python run_analysis.py --start 2021-01 --end 2025-12
    python run_analysis.py --skip-download          # use files already in data/raw
    python run_analysis.py --data-dir data/sample --skip-download   # offline demo
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import date
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent / "src"))

from nzelec import analysis, plots  # noqa: E402
from nzelec.download import download_months  # noqa: E402
from nzelec.load import load_daily, read_half_hourly  # noqa: E402

ROOT = Path(__file__).parent


def default_range() -> tuple[str, str]:
    """Last 36 complete months (EMI publishes each month shortly after it ends)."""
    end = pd.Period(date.today(), "M") - 1
    start = end - 35
    return start.strftime("%Y-%m"), end.strftime("%Y-%m")


def main() -> None:
    start_default, end_default = default_range()
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--start", default=start_default, help="first month, YYYY-MM")
    p.add_argument("--end", default=end_default, help="last month, YYYY-MM")
    p.add_argument("--data-dir", type=Path, default=ROOT / "data" / "raw")
    p.add_argument("--out-dir", type=Path, default=ROOT / "outputs")
    p.add_argument("--skip-download", action="store_true")
    args = p.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    if not args.skip_download:
        download_months(args.start, args.end, args.data_dir)

    files = sorted(args.data_dir.glob("*_Generation_MD.csv"))
    daily = load_daily(files)

    tables = args.out_dir / "tables"
    figs = args.out_dir / "figures"
    tables.mkdir(parents=True, exist_ok=True)

    monthly = analysis.monthly_by_group(daily)
    m_share = analysis.renewable_share(daily, "M")
    y_share = analysis.renewable_share(daily, "Y")
    rolling = analysis.rolling_12m_share(m_share)
    seasonal = analysis.seasonal_profile(daily)

    monthly.round(2).to_csv(tables / "monthly_generation_by_fuel_gwh.csv")
    m_share.join(rolling).round(2).to_csv(tables / "renewable_share_monthly.csv")
    y_share.round(2).to_csv(tables / "renewable_share_yearly.csv")
    seasonal.round(2).to_csv(tables / "seasonal_mix_pct.csv")

    plots.plot_generation_mix(monthly, figs / "generation_mix.png")
    plots.plot_renewable_share(m_share, rolling, figs / "renewable_share.png")
    plots.plot_seasonal(seasonal, figs / "seasonal_mix.png")

    # Daily shape from the most recent month (solar & peaking gas show up here).
    latest = files[-1]
    hh = read_half_hourly(latest)
    hh.attrs["n_days"] = pd.read_csv(latest, usecols=["Trading_Date"])["Trading_Date"].nunique()
    label = pd.to_datetime(latest.name[:6], format="%Y%m").strftime("%b %Y")
    plots.plot_daily_shape(analysis.daily_shape(hh), figs / "daily_profile.png", label)

    findings = analysis.headline_findings(daily)
    (args.out_dir / "findings.json").write_text(json.dumps(findings, indent=2, default=str))

    print("\n=== Headline findings ===")
    print(f"Period:                 {findings['period']}")
    print(f"Total grid generation:  {findings['total_twh']} TWh")
    print(f"Renewable share:        {findings['renewable_pct_overall']}%")
    for yr, pct in findings["renewable_pct_by_year"].items():
        print(f"  {yr}: {pct}%")
    print(f"Largest source:         {findings['largest_source']} ({findings['largest_source_pct']}%)")
    print(f"Most renewable month:   {findings['best_month'][0]} ({findings['best_month'][1]}%)")
    print(f"Least renewable month:  {findings['worst_month'][0]} ({findings['worst_month'][1]}%)")
    print(f"\nTables  -> {tables}\nFigures -> {figs}")


if __name__ == "__main__":
    main()
