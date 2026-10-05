"""Generate SYNTHETIC files in the EMI Generation_MD format.

These are NOT real NZ data. They exist so the tests and an offline demo can run
without network access. Magnitudes are rough and only roughly NZ-shaped.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

UNITS = [  # (Gen_Code, Fuel_Code, typical MW)
    ("HYD1", "Hydro", 2600),
    ("GEO1", "Geo", 900),
    ("WND1", "Wind", 350),
    ("SOL1", "Solar", 40),
    ("GAS1", "Gas", 450),
    ("RNK1", "Gas&Coal", 250),
    ("WOD1", "Wood", 30),
]


def make_month(ym: str, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed + int(ym))
    start = pd.Timestamp(f"{ym[:4]}-{ym[4:]}-01")
    days = pd.date_range(start, start + pd.offsets.MonthEnd(0), freq="D")
    month = start.month
    winter = np.cos((month - 7) / 12 * 2 * np.pi)  # 1 in July, -1 in January
    hours = (np.arange(48) + 0.5) / 2
    demand_shape = 1 + 0.15 * np.sin((hours - 6) / 24 * 2 * np.pi)
    solar_shape = np.clip(np.sin((hours - 6) / 13 * np.pi), 0, None) * (1 - 0.4 * winter)

    rows = []
    for d in days:
        for code, fuel, mw in UNITS:
            if fuel == "Solar":
                shape = solar_shape * 2
            elif fuel in ("Gas", "Gas&Coal"):
                shape = demand_shape * (1 + 0.6 * winter) ** 2  # thermal fills winter peak
            elif fuel == "Hydro":
                shape = demand_shape * (1 - 0.1 * winter)
            else:
                shape = np.ones(48)
            noise = rng.normal(1, 0.08, 48).clip(0.5)
            kwh = np.clip(mw * shape * noise * 1000 * 0.5, 0, None).round()
            rows.append([f"S{code}", f"P{code}", "NWK", code, fuel, "TECH", d.strftime("%Y-%m-%d"), *kwh])
    cols = ["Site_Code", "POC_Code", "Nwk_Code", "Gen_Code", "Fuel_Code", "Tech_Code", "Trading_Date"]
    return pd.DataFrame(rows, columns=cols + [f"TP{i}" for i in range(1, 49)])


def write_sample(dest: Path, months: list[str]) -> list[Path]:
    dest.mkdir(parents=True, exist_ok=True)
    paths = []
    for ym in months:
        p = dest / f"{ym}_Generation_MD.csv"
        make_month(ym).to_csv(p, index=False)
        paths.append(p)
    return paths


if __name__ == "__main__":
    from datetime import date

    end = pd.Period(date.today(), "M") - 1
    months = [(end - i).strftime("%Y%m") for i in range(23, -1, -1)]
    out = Path(__file__).resolve().parent.parent / "data" / "sample"
    write_sample(out, months)
    print(f"Wrote {len(months)} SYNTHETIC months to {out}")
