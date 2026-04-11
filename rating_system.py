"""
Wave quality rating system.

Ratings are on a 1–10 scale and combine wave height, wave period,
and wind speed into a single score that reflects real-world surf
conditions.
"""

from __future__ import annotations
from typing import List, Dict, Any, Tuple


# ---------------------------------------------------------------------------
# Scoring helpers
# ---------------------------------------------------------------------------

def _height_score(height: float) -> float:
    """
    Score wave height on a 0–10 scale.

    Ideal range: 0.5 – 2.5 m.
    Below 0.5 m → flat / unsurfable.
    Above 3.5 m → dangerously large for most surfers.
    """
    if height < 0.3:
        return 0.0
    if height < 0.5:
        # Ramp up from 0 → 4
        return round(4.0 * (height - 0.3) / 0.2, 2)
    if height <= 2.5:
        # Sweet spot: linear 5 → 10
        return round(5.0 + 5.0 * (height - 0.5) / 2.0, 2)
    if height <= 3.5:
        # Getting big: 10 → 5
        return round(10.0 - 5.0 * (height - 2.5) / 1.0, 2)
    # Too big
    return max(0.0, round(5.0 - 2.0 * (height - 3.5), 2))


def _period_score(period: float) -> float:
    """
    Score wave period on a 0–10 scale.

    Ideal range: 8 – 14 s (clean, powerful swell).
    Below 5 s → choppy wind-swell.
    Above 18 s → very long-period, often closes out.
    """
    if period < 4:
        return 0.0
    if period < 8:
        # Ramp up 0 → 6
        return round(6.0 * (period - 4) / 4.0, 2)
    if period <= 14:
        # Sweet spot: 7 → 10
        return round(7.0 + 3.0 * (period - 8) / 6.0, 2)
    if period <= 18:
        # Slightly too long: 10 → 7
        return round(10.0 - 3.0 * (period - 14) / 4.0, 2)
    return 7.0


def _wind_score(wind: float) -> float:
    """
    Score wind speed on a 0–10 scale.

    < 5 m/s  → glassy / light offshore: perfect.
    5 – 10   → manageable onshore.
    > 15 m/s → blown-out.
    """
    if wind < 5:
        return 10.0
    if wind <= 10:
        return round(10.0 - 4.0 * (wind - 5) / 5.0, 2)
    if wind <= 15:
        return round(6.0 - 4.0 * (wind - 10) / 5.0, 2)
    return max(0.0, round(2.0 - 0.2 * (wind - 15), 2))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def calculate_rating(height: float, period: float, wind: float) -> float:
    """
    Return a wave quality rating between 1.0 and 10.0.

    Weights:
        Wave height  40 %
        Wave period  35 %
        Wind speed   25 %
    """
    score = (
        0.40 * _height_score(height)
        + 0.35 * _period_score(period)
        + 0.25 * _wind_score(wind)
    )
    # Clamp to [1, 10] and round to one decimal place
    return round(max(1.0, min(10.0, score)), 1)


def get_rating_label(rating: float) -> str:
    """Return a short human-readable label for a numeric rating."""
    if rating >= 9:
        return "Epic 🔥"
    if rating >= 7:
        return "Good 🟢"
    if rating >= 5:
        return "Fair 🟡"
    if rating >= 3:
        return "Poor 🟠"
    return "Flat / Blown-out 🔴"


def get_rating_explanation(height: float, period: float, wind: float) -> str:
    """
    Return a one-line plain-English explanation of the main factors
    driving the rating.
    """
    parts: List[str] = []

    if height < 0.5:
        parts.append("waves too small")
    elif height > 3.0:
        parts.append("waves very large")
    else:
        parts.append(f"{height:.1f} m waves")

    if period < 6:
        parts.append("choppy short-period swell")
    elif period >= 8:
        parts.append(f"{period:.0f} s clean swell")

    if wind < 5:
        parts.append("light winds")
    elif wind < 10:
        parts.append(f"{wind:.0f} m/s moderate wind")
    else:
        parts.append(f"{wind:.0f} m/s strong wind")

    return " · ".join(parts)


def find_good_wave_windows(
    hours: List[Dict[str, Any]],
    min_rating: float = 7.0,
    min_consecutive: int = 2,
) -> List[Dict[str, Any]]:
    """
    Identify contiguous time windows where the wave quality rating is
    at or above *min_rating* for at least *min_consecutive* hours.

    Each element of *hours* must have keys: ``time``, ``height``,
    ``period``, ``wind``.  ``time`` should be a :class:`datetime`.

    Returns a list of window dicts::

        {
            "start":      datetime,
            "end":        datetime,
            "peak_rating": float,
            "avg_rating":  float,
            "hours":       [hour_dict, ...],
        }
    """
    # Attach ratings
    rated: List[Tuple[Dict[str, Any], float]] = []
    for h in hours:
        r = calculate_rating(h["height"], h["period"], h["wind"])
        rated.append((h, r))

    windows: List[Dict[str, Any]] = []
    i = 0
    while i < len(rated):
        h, r = rated[i]
        if r >= min_rating:
            # Start of a potential window
            window_hours = [h]
            window_ratings = [r]
            j = i + 1
            while j < len(rated) and rated[j][1] >= min_rating:
                window_hours.append(rated[j][0])
                window_ratings.append(rated[j][1])
                j += 1

            if len(window_hours) >= min_consecutive:
                windows.append({
                    "start": window_hours[0]["time"],
                    "end": window_hours[-1]["time"],
                    "peak_rating": max(window_ratings),
                    "avg_rating": round(
                        sum(window_ratings) / len(window_ratings), 1
                    ),
                    "hours": window_hours,
                })
            i = j  # skip past this window
        else:
            i += 1

    return windows


def format_good_windows_message(
    windows: List[Dict[str, Any]],
    beach: str,
) -> str:
    """
    Format a Telegram-ready notification message for detected good-wave
    windows.  Returns an empty string when *windows* is empty.
    """
    if not windows:
        return ""

    lines = [f"🏄 *Good surf detected at {beach.title()}!*\n"]
    for idx, w in enumerate(windows, 1):
        start_str = w["start"].strftime("%a %d %b %H:%M")
        end_str = w["end"].strftime("%H:%M")
        label = get_rating_label(w["peak_rating"])
        lines.append(
            f"*Window {idx}:* {start_str} → {end_str}\n"
            f"  Peak rating: *{w['peak_rating']}/10* – {label}\n"
            f"  Avg rating:  {w['avg_rating']}/10"
        )

    return "\n\n".join(lines)
