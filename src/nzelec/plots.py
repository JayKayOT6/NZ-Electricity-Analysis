"""Charts. Static PNGs for the README, styled consistently.

Colours follow the fuel group (never its rank), in a fixed colour-blind-checked order.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

SURFACE = "#fcfcfb"
TEXT = "#0b0b0b"
TEXT_2 = "#52514e"
GRID = "#e4e3df"

FUEL_COLOURS = {
    "Hydro": "#2a78d6",
    "Geothermal": "#eb6834",
    "Wind": "#1baf7a",
    "Solar": "#eda100",
    "Gas": "#e87ba4",
    "Coal & dual-fuel": "#008300",
    "Other": "#4a3aa7",
}
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _style(ax, title: str, ylabel: str) -> None:
    fig = ax.figure
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)
    ax.set_title(title, loc="left", fontsize=13, color=TEXT, pad=12, fontweight="semibold")
    ax.set_ylabel(ylabel, color=TEXT_2)
    ax.tick_params(colors=TEXT_2, length=0)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def _legend(ax, ncol: int = 4) -> None:
    leg = ax.legend(frameon=False, ncol=ncol, loc="upper left", bbox_to_anchor=(0, -0.12), fontsize=9)
    for t in leg.get_texts():
        t.set_color(TEXT_2)


def _save(fig, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, dpi=160, facecolor=SURFACE)
    plt.close(fig)
    return path


def plot_generation_mix(monthly: pd.DataFrame, path: Path) -> Path:
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.stackplot(
        monthly.index,
        [monthly[c] for c in monthly.columns],
        labels=monthly.columns,
        colors=[FUEL_COLOURS[c] for c in monthly.columns],
        edgecolor=SURFACE,
        linewidth=0.6,
    )
    _style(ax, "Monthly grid generation by fuel", "GWh per month")
    ax.set_ylim(bottom=0)
    _legend(ax)
    return _save(fig, path)


def plot_renewable_share(monthly_share: pd.DataFrame, rolling: pd.Series, path: Path) -> Path:
    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.plot(monthly_share.index, monthly_share["renewable_pct"], color="#9fc3ee", linewidth=1.5, label="Monthly")
    ax.plot(rolling.index, rolling, color="#2a78d6", linewidth=2.5, label="12-month rolling")
    last = rolling.dropna()
    if not last.empty:
        ax.annotate(
            f"{last.iloc[-1]:.1f}%",
            (last.index[-1], last.iloc[-1]),
            xytext=(6, 0),
            textcoords="offset points",
            va="center",
            color=TEXT,
            fontsize=10,
            fontweight="semibold",
        )
    _style(ax, "Renewable share of grid generation", "% of generation")
    lo = max(0, monthly_share["renewable_pct"].min() - 5)
    ax.set_ylim(lo, 100)
    _legend(ax, ncol=2)
    return _save(fig, path)


def plot_seasonal(seasonal: pd.DataFrame, path: Path) -> Path:
    fig, ax = plt.subplots(figsize=(10, 5))
    bottom = pd.Series(0.0, index=seasonal.index)
    for col in seasonal.columns:
        ax.bar(
            list(range(len(seasonal))),
            seasonal[col],
            bottom=bottom,
            color=FUEL_COLOURS[col],
            edgecolor=SURFACE,
            linewidth=1.5,
            width=0.7,
            label=col,
        )
        bottom += seasonal[col]
    ax.set_xticks(range(len(seasonal)), [MONTHS[m - 1] for m in seasonal.index])
    _style(ax, "Average fuel mix by calendar month", "% of generation")
    ax.set_ylim(0, 100)
    _legend(ax)
    return _save(fig, path)


def plot_daily_shape(shape: pd.DataFrame, path: Path, label: str = "") -> Path:
    fig, ax = plt.subplots(figsize=(10, 5))
    hours = (shape.index - 1) / 2  # TP1 = 00:00-00:30
    ax.stackplot(
        hours,
        [shape[c] for c in shape.columns],
        labels=shape.columns,
        colors=[FUEL_COLOURS[c] for c in shape.columns],
        edgecolor=SURFACE,
        linewidth=0.6,
    )
    ax.set_xticks(range(0, 25, 3), [f"{h:02d}:00" for h in range(0, 25, 3)])
    ax.set_xlim(0, 23.5)
    title = "Average daily generation profile" + (f" ({label})" if label else "")
    _style(ax, title, "Average MW")
    _legend(ax)
    return _save(fig, path)
