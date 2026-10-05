import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

from make_sample import write_sample  # noqa: E402
from nzelec import analysis  # noqa: E402
from nzelec.download import month_range  # noqa: E402
from nzelec.load import load_daily, read_half_hourly, read_month  # noqa: E402

MONTHS = [f"2024{m:02d}" for m in range(1, 13)] + ["202501"]


@pytest.fixture(scope="module")
def files(tmp_path_factory):
    return write_sample(tmp_path_factory.mktemp("raw"), MONTHS)


@pytest.fixture(scope="module")
def daily(files):
    return load_daily(files)


def test_month_range():
    assert month_range("2023-11", "2024-02") == ["202311", "202312", "202401", "202402"]
    with pytest.raises(ValueError):
        month_range("2024-02", "2024-01")


def test_read_month_conserves_energy(files):
    raw = pd.read_csv(files[0])
    tp = [c for c in raw.columns if c.startswith("TP")]
    assert read_month(files[0])["kwh"].sum() == pytest.approx(raw[tp].to_numpy().sum())


def test_dst_columns_are_counted(tmp_path, files):
    raw = pd.read_csv(files[0])
    raw["TP49"] = 1000.0
    raw["TP50"] = 1000.0
    p = tmp_path / "202404_Generation_MD.csv"
    raw.to_csv(p, index=False)
    extra = read_month(p)["kwh"].sum() - read_month(files[0])["kwh"].sum()
    assert extra == pytest.approx(2000 * len(raw))


def test_dual_fuel_and_wood_are_grouped(daily):
    assert set(daily.loc[daily.fuel_code == "gas&coal", "group"]) == {"Coal & dual-fuel"}
    assert daily.loc[daily.fuel_code == "wood", "renewable"].all()
    assert not daily.loc[daily.fuel_code == "gas", "renewable"].any()


def test_monthly_totals_match_daily(daily):
    m = analysis.monthly_by_group(daily)
    assert len(m) == len(MONTHS)
    assert m.to_numpy().sum() == pytest.approx(daily["gwh"].sum())


def test_renewable_share_bounds(daily):
    share = analysis.renewable_share(daily, "M")
    assert share["renewable_pct"].between(0, 100).all()
    assert (share["renewable_gwh"] <= share["total_gwh"]).all()


def test_rolling_needs_twelve_months(daily):
    r = analysis.rolling_12m_share(analysis.renewable_share(daily, "M"))
    assert r.isna().sum() == 11
    assert r.notna().sum() == len(MONTHS) - 11


def test_seasonal_rows_sum_to_100(daily):
    s = analysis.seasonal_profile(daily)
    assert s.sum(axis=1).round(6).eq(100).all()


def test_daily_shape_has_48_periods(files):
    hh = read_half_hourly(files[0])
    hh.attrs["n_days"] = 31
    shape = analysis.daily_shape(hh)
    assert list(shape.index) == list(range(1, 49))
    assert (shape["Solar"].iloc[:8] < shape["Solar"].iloc[22:28].mean()).all()  # no sun at night


def test_missing_files_error():
    with pytest.raises(FileNotFoundError):
        load_daily([])
