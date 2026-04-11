"""
Professional surf forecast graph generator.

Produces a publication-quality multi-panel figure that shows:
  • Wave height (smoothed spline) with colour-coded quality fill
  • Wave period as a secondary line
  • Wind speed on a twin axis
  • Per-point quality rating (1–10) as a colour-mapped scatter overlay
  • A "conditions summary" annotation box listing the best time windows
"""

from __future__ import annotations

import textwrap
from typing import List, Dict, Any

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.gridspec as gridspec
from matplotlib.colors import LinearSegmentedColormap
import numpy as np
import pandas as pd
import seaborn as sns
from scipy.interpolate import make_interp_spline

from rating_system import (
    calculate_rating,
    get_rating_label,
    find_good_wave_windows,
)

# ---------------------------------------------------------------------------
# Colour palette
# ---------------------------------------------------------------------------

# Rating colour map: red (1) → amber (5) → green (10)
RATING_CMAP = LinearSegmentedColormap.from_list(
    "surf_rating",
    [
        (0.0,  "#d62728"),   # 1  – flat / blown-out
        (0.25, "#ff7f0e"),   # 3  – poor
        (0.50, "#f7d060"),   # 5  – fair
        (0.75, "#2ca02c"),   # 7  – good
        (1.00, "#1a7abf"),   # 10 – epic
    ],
)

WAVE_COLOR   = "#1a7abf"   # deep ocean blue
PERIOD_COLOR = "#17becf"   # teal
WIND_COLOR   = "#e05c5c"   # coral-red
BG_COLOR     = "#0d1b2a"   # dark navy background
PANEL_COLOR  = "#112233"   # slightly lighter panel
GRID_COLOR   = "#1e3a5f"   # subtle grid lines
TEXT_COLOR   = "#e8f4fd"   # near-white text


def _build_dataframe(hours: List[Dict[str, Any]]) -> pd.DataFrame:
    """Convert the hourly list from surf_tools into a thinned DataFrame."""
    rows = []
    for h in hours:
        rows.append({
            "time":   h["time"],
            "height": h["height"],
            "period": h["period"],
            "wind":   h["wind"],
            "rating": h.get("rating", calculate_rating(h["height"], h["period"], h["wind"])),
        })

    df = pd.DataFrame(rows)
    # Thin to every 3 hours for a readable x-axis (keep full resolution for
    # the rating scatter so peaks are not missed)
    df_thin = df.iloc[::3].reset_index(drop=True)
    return df, df_thin


def _smooth(x: np.ndarray, y: np.ndarray, points: int = 400) -> tuple:
    """Return smoothed (x_s, y_s) using a cubic B-spline."""
    if len(x) < 4:
        return x.astype(float), y.astype(float)
    spline = make_interp_spline(x, y, k=3)
    x_s = np.linspace(x.min(), x.max(), points)
    return x_s, spline(x_s)


def _conditions_summary(windows, beach: str) -> str:
    """Build the text for the conditions summary annotation box."""
    if not windows:
        return "No windows with rating ≥ 7 detected\nin this forecast period."

    lines = [f"Best surf windows at {beach.title()}:"]
    for w in windows[:4]:  # cap at 4 to keep the box compact
        start = w["start"].strftime("%a %d %b %H:%M")
        end   = w["end"].strftime("%H:%M")
        lines.append(
            f"  {start} → {end}  "
            f"peak {w['peak_rating']}/10 · avg {w['avg_rating']}/10"
        )
    return "\n".join(lines)


def create_wave_graph(hours: List[Dict[str, Any]], beach: str) -> str:
    """
    Generate a professional surf forecast graph.

    Parameters
    ----------
    hours : list of dicts
        Hourly data from ``surf_tools.get_surf_forecast``.
        Each dict must have: ``time`` (datetime), ``height``, ``period``,
        ``wind``, and optionally ``rating``.
    beach : str
        Beach name used in the title and filename.

    Returns
    -------
    str
        Path to the saved PNG file.
    """
    sns.set_theme(style="dark")

    df_full, df = _build_dataframe(hours)

    x      = np.arange(len(df))
    labels = [t.strftime("%-d.%m %-I%p").lower() for t in df["time"]]

    # Detect good windows from the full-resolution data
    windows = find_good_wave_windows(df_full.to_dict("records"), min_rating=7.0)

    # Overall best rating for the headline
    best_rating  = df_full["rating"].max()
    best_label   = get_rating_label(best_rating)
    avg_rating   = round(df_full["rating"].mean(), 1)
    avg_period   = df_full["period"].mean()

    # -----------------------------------------------------------------------
    # Figure layout: 3 rows
    #   row 0 (tall)  – wave height + rating fill + wind
    #   row 1 (short) – wave period
    #   row 2 (short) – rating bar
    # -----------------------------------------------------------------------
    fig = plt.figure(figsize=(16, 11), facecolor=BG_COLOR)
    gs  = gridspec.GridSpec(
        3, 1,
        height_ratios=[5, 2, 2],
        hspace=0.08,
        left=0.07, right=0.93,
        top=0.88, bottom=0.12,
    )

    ax_wave   = fig.add_subplot(gs[0])
    ax_period = fig.add_subplot(gs[1], sharex=ax_wave)
    ax_rating = fig.add_subplot(gs[2], sharex=ax_wave)

    for ax in (ax_wave, ax_period, ax_rating):
        ax.set_facecolor(PANEL_COLOR)
        ax.tick_params(colors=TEXT_COLOR, labelsize=9)
        for spine in ax.spines.values():
            spine.set_edgecolor(GRID_COLOR)
        ax.grid(True, linestyle="--", linewidth=0.5, color=GRID_COLOR, alpha=0.6)

    # -----------------------------------------------------------------------
    # Panel 0 – Wave height
    # -----------------------------------------------------------------------
    x_s, y_s = _smooth(x, df["height"].values)

    # Colour-coded fill under the wave curve (mapped to rating)
    for i in range(len(df) - 1):
        r_norm = (df["rating"].iloc[i] - 1) / 9.0   # normalise to [0, 1]
        fill_color = RATING_CMAP(r_norm)
        ax_wave.fill_between(
            [x[i], x[i + 1]],
            [df["height"].iloc[i], df["height"].iloc[i + 1]],
            color=fill_color,
            alpha=0.35,
        )

    # Smooth wave line
    ax_wave.plot(x_s, y_s, color=WAVE_COLOR, linewidth=2.5,
                 label="Wave height (m)", zorder=3)

    # Rating scatter dots on the wave line (colour = rating)
    scatter_y = np.interp(x, x_s, y_s)
    sc = ax_wave.scatter(
        x, scatter_y,
        c=df["rating"].values,
        cmap=RATING_CMAP,
        vmin=1, vmax=10,
        s=60, zorder=4, edgecolors="white", linewidths=0.4,
    )

    # Wind on twin axis
    ax_wind = ax_wave.twinx()
    ax_wind.set_facecolor(PANEL_COLOR)
    ax_wind.plot(x, df["wind"], color=WIND_COLOR, linewidth=1.8,
                 linestyle="--", label="Wind (m/s)", alpha=0.85)
    ax_wind.set_ylabel("Wind speed (m/s)", color=WIND_COLOR, fontsize=10,
                       labelpad=8)
    ax_wind.tick_params(axis="y", colors=WIND_COLOR, labelsize=9)
    ax_wind.spines["right"].set_edgecolor(WIND_COLOR)

    ax_wave.set_ylabel("Wave height (m)", color=WAVE_COLOR, fontsize=11,
                       labelpad=8)
    ax_wave.tick_params(axis="y", colors=WAVE_COLOR)

    # Colourbar for rating
    cbar = fig.colorbar(sc, ax=ax_wave, pad=0.12, fraction=0.018, aspect=25)
    cbar.set_label("Quality rating", color=TEXT_COLOR, fontsize=9)
    cbar.ax.yaxis.set_tick_params(color=TEXT_COLOR, labelsize=8)
    plt.setp(cbar.ax.yaxis.get_ticklabels(), color=TEXT_COLOR)

    # Legend
    wave_patch = mpatches.Patch(color=WAVE_COLOR, label="Wave height (m)")
    wind_patch = mpatches.Patch(color=WIND_COLOR, label="Wind speed (m/s)")
    ax_wave.legend(
        handles=[wave_patch, wind_patch],
        loc="upper left", fontsize=9,
        facecolor=BG_COLOR, edgecolor=GRID_COLOR, labelcolor=TEXT_COLOR,
    )

    # -----------------------------------------------------------------------
    # Panel 1 – Wave period
    # -----------------------------------------------------------------------
    x_sp, y_sp = _smooth(x, df["period"].values)
    ax_period.plot(x_sp, y_sp, color=PERIOD_COLOR, linewidth=2.0,
                   label="Wave period (s)")
    ax_period.fill_between(x_sp, y_sp, alpha=0.15, color=PERIOD_COLOR)
    ax_period.set_ylabel("Period (s)", color=PERIOD_COLOR, fontsize=10,
                         labelpad=8)
    ax_period.tick_params(axis="y", colors=PERIOD_COLOR)
    ax_period.axhspan(8, 14, color="#2ca02c", alpha=0.08,
                      label="Ideal period (8–14 s)")
    ax_period.legend(
        loc="upper left", fontsize=8,
        facecolor=BG_COLOR, edgecolor=GRID_COLOR, labelcolor=TEXT_COLOR,
    )

    # -----------------------------------------------------------------------
    # Panel 2 – Rating bar chart
    # -----------------------------------------------------------------------
    bar_colors = [RATING_CMAP((r - 1) / 9.0) for r in df["rating"]]
    ax_rating.bar(x, df["rating"], color=bar_colors, width=0.7, zorder=3)
    ax_rating.axhline(7, color="#2ca02c", linewidth=1.2, linestyle="--",
                      alpha=0.8, label="Good threshold (7)")
    ax_rating.set_ylim(0, 10.5)
    ax_rating.set_ylabel("Rating /10", color=TEXT_COLOR, fontsize=10,
                         labelpad=8)
    ax_rating.tick_params(axis="y", colors=TEXT_COLOR)
    ax_rating.legend(
        loc="upper left", fontsize=8,
        facecolor=BG_COLOR, edgecolor=GRID_COLOR, labelcolor=TEXT_COLOR,
    )

    # Shared x-axis ticks (only show on bottom panel)
    plt.setp(ax_wave.get_xticklabels(), visible=False)
    plt.setp(ax_period.get_xticklabels(), visible=False)
    ax_rating.set_xticks(x)
    ax_rating.set_xticklabels(labels, rotation=30, ha="right",
                               fontsize=8, color=TEXT_COLOR)

    # -----------------------------------------------------------------------
    # Title block
    # -----------------------------------------------------------------------
    fig.text(
        0.5, 0.945,
        f"{beach.title()} Surf Forecast",
        ha="center", va="center",
        fontsize=20, fontweight="bold", color=TEXT_COLOR,
    )
    fig.text(
        0.5, 0.915,
        (
            f"Best rating: {best_rating}/10 – {best_label}   |   "
            f"Avg rating: {avg_rating}/10   |   "
            f"Avg wave period: {avg_period:.1f} s"
        ),
        ha="center", va="center",
        fontsize=11, color="#a8c8e8",
    )

    # -----------------------------------------------------------------------
    # Conditions summary box (bottom-right of wave panel)
    # -----------------------------------------------------------------------
    summary_text = _conditions_summary(windows, beach)
    ax_wave.text(
        0.99, 0.97,
        summary_text,
        transform=ax_wave.transAxes,
        ha="right", va="top",
        fontsize=8, color=TEXT_COLOR,
        linespacing=1.6,
        bbox=dict(
            boxstyle="round,pad=0.5",
            facecolor=BG_COLOR,
            edgecolor="#2ca02c",
            alpha=0.85,
        ),
    )

    # -----------------------------------------------------------------------
    # Save
    # -----------------------------------------------------------------------
    filename = f"{beach.replace(' ', '_')}_surf.png"
    fig.savefig(filename, dpi=160, facecolor=BG_COLOR)
    plt.close(fig)

    return filename
