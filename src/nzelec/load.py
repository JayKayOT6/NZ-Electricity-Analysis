"""Load EMI Generation_MD files into a tidy table.

Each raw file has one row per generating unit per trading day, with half-hourly
trading-period columns TP1..TP48 (TP49/TP50 appear on daylight-saving change
days). Values are energy in kWh.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

TP_PATTERN = re.compile(r"^TP(\d+)$")

# Raw EMI fuel codes -> reporting groups (fixed order, used for colours too).
FUEL_GROUPS = {
    "hydro": "Hydro",
    "geo": "Geothermal",
    "wind": "Wind",
    "solar": "Solar",
    "gas": "Gas",
    "coal": "Coal & dual-fuel",
    "gas&coal": "Coal & dual-fuel",  # Huntly Rankine units burn gas or coal
    "coal&gas": "Coal & dual-fuel",
    "diesel": "Other",
    "wood": "Other",
}
GROUP_ORDER = ["Hydro", "Geothermal", "Wind", "Solar", "Gas", "Coal & dual-fuel", "Other"]

# Fuels counted as renewable (wood = biomass cogeneration).
RENEWABLE_FUELS = {"hydro", "geo", "wind", "solar", "wood"}


def read_month(path: Path) -> pd.DataFrame:
    """Read one month's file and return daily energy per fuel (GWh)."""
    raw = pd.read_csv(path)
    tp_cols = [c for c in raw.columns if TP_PATTERN.match(str(c))]
    if not tp_cols or "Fuel_Code" not in raw.columns or "Trading_Date" not in raw.columns:
        raise ValueError(f"{path.name}: unexpected columns {list(raw.columns)[:10]}")

    df = pd.DataFrame(
        {
            "date": pd.to_datetime(raw["Trading_Date"]),
            "fuel_code": raw["Fuel_Code"].astype(str).str.strip().str.lower(),
            "kwh": raw[tp_cols].apply(pd.to_numeric, errors="coerce").fillna(0).sum(axis=1),
        }
    )
    return df.groupby(["date", "fuel_code"], as_index=False)["kwh"].sum()


def read_half_hourly(path: Path) -> pd.DataFrame:
    """Long-format half-hourly energy per fuel group for one month (for daily profiles)."""
    raw = pd.read_csv(path)
    tp_cols = [c for c in raw.columns if TP_PATTERN.match(str(c))]
    raw["group"] = raw["Fuel_Code"].astype(str).str.strip().str.lower().map(FUEL_GROUPS).fillna("Other")
    long = raw.melt(id_vars=["group"], value_vars=tp_cols, var_name="tp", value_name="kwh")
    long["tp"] = long["tp"].str[2:].astype(int)
    long["kwh"] = pd.to_numeric(long["kwh"], errors="coerce").fillna(0)
    return long[long["tp"] <= 48]  # drop DST extras so every day has 48 periods


def load_daily(paths: list[Path]) -> pd.DataFrame:
    """Daily generation by fuel across many monthly files, with group + renewable flag."""
    if not paths:
        raise FileNotFoundError("No Generation_MD files found - run the download step first.")
    df = pd.concat([read_month(p) for p in sorted(paths)], ignore_index=True)
    df = df.groupby(["date", "fuel_code"], as_index=False)["kwh"].sum()
    df["group"] = df["fuel_code"].map(FUEL_GROUPS).fillna("Other")
    df["renewable"] = df["fuel_code"].isin(RENEWABLE_FUELS)
    df["gwh"] = df["kwh"] / 1e6
    return df.drop(columns="kwh")
