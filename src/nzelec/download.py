"""Download monthly generation files from the Electricity Authority's EMI portal.

Source: Electricity Market Information (EMI), "Generation_MD" dataset - metered
half-hourly generation (kWh) for every grid-connected generating unit.
https://www.emi.ea.govt.nz/Wholesale/Datasets/Generation/Generation_MD
"""

from __future__ import annotations

import logging
from pathlib import Path

import requests

BASE_URL = "https://www.emi.ea.govt.nz/Wholesale/Datasets/Generation/Generation_MD"
log = logging.getLogger(__name__)


def month_range(start: str, end: str) -> list[str]:
    """Return YYYYMM strings from start to end inclusive, e.g. ('2023-01', '2023-03')."""
    sy, sm = (int(x) for x in start.split("-"))
    ey, em = (int(x) for x in end.split("-"))
    if (sy, sm) > (ey, em):
        raise ValueError(f"start {start} is after end {end}")
    months = []
    y, m = sy, sm
    while (y, m) <= (ey, em):
        months.append(f"{y:04d}{m:02d}")
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return months


def download_months(start: str, end: str, dest: Path, overwrite: bool = False) -> list[Path]:
    """Download each month's CSV into dest, skipping files already present."""
    dest.mkdir(parents=True, exist_ok=True)
    saved: list[Path] = []
    with requests.Session() as session:
        for ym in month_range(start, end):
            name = f"{ym}_Generation_MD.csv"
            path = dest / name
            if path.exists() and not overwrite:
                log.info("exists, skipping %s", name)
                saved.append(path)
                continue
            url = f"{BASE_URL}/{name}"
            log.info("downloading %s", url)
            resp = session.get(url, timeout=120)
            if resp.status_code == 404:
                log.warning("not published yet: %s", name)
                continue
            resp.raise_for_status()
            path.write_bytes(resp.content)
            saved.append(path)
    return saved
