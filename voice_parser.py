"""
Voice command parser for the Surf Bot.

Parses transcribed voice text (Hebrew or English) to extract:
  - beach name
  - forecast duration in days
  - detected language (he / en)

Usage:
    from voice_parser import parse_voice_command
    beach, days, lang = parse_voice_command(text, detected_lang)
"""

from __future__ import annotations
import re

# ---------------------------------------------------------------------------
# Beach name mappings
# ---------------------------------------------------------------------------

# Maps every recognised alias → canonical beach key (must match surf_tools.py)
BEACH_ALIASES: dict[str, str] = {
    # English
    "habonim": "habonim",
    "tel aviv": "tel aviv",
    "tel-aviv": "tel aviv",
    "telaviv": "tel aviv",
    "netanya": "netanya",
    "herzliya": "herzliya",
    "herzelia": "herzliya",
    "ashdod": "ashdod",
    "haifa": "haifa",
    # Hebrew – common beach / city names
    "חוף סוקולוב": "habonim",
    "סוקולוב": "habonim",
    "חבונים": "habonim",
    "הבונים": "habonim",
    "תל אביב": "tel aviv",
    "נתניה": "netanya",
    "הרצליה": "herzliya",
    "אשדוד": "ashdod",
    "חיפה": "haifa",
    "נהריה": "haifa",   # Nahariya – closest supported coord is Haifa
}

# ---------------------------------------------------------------------------
# Duration keyword mappings  →  number of days
# ---------------------------------------------------------------------------

DURATION_PATTERNS: list[tuple[re.Pattern[str], int]] = [
    # English
    (re.compile(r"\b7\s*days?\b", re.IGNORECASE), 7),
    (re.compile(r"\bnext\s+week\b", re.IGNORECASE), 7),
    (re.compile(r"\bupcoming\s+days?\b", re.IGNORECASE), 7),
    (re.compile(r"\bweek\b", re.IGNORECASE), 7),
    (re.compile(r"\btomorrow\b", re.IGNORECASE), 2),
    (re.compile(r"\btoday\b", re.IGNORECASE), 1),
    # Hebrew
    (re.compile(r"7\s*ימים"), 7),
    (re.compile(r"הימים\s+הקרובים"), 7),
    (re.compile(r"\bשבוע\b"), 7),
    (re.compile(r"\bמחר\b"), 2),
    (re.compile(r"\bהיום\b"), 1),
]

# ---------------------------------------------------------------------------
# Language detection helpers
# ---------------------------------------------------------------------------

_HEBREW_RE = re.compile(r"[\u0590-\u05FF]")


def _detect_language(text: str) -> str:
    """Return 'he' if the text contains Hebrew characters, else 'en'."""
    return "he" if _HEBREW_RE.search(text) else "en"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_voice_command(text: str, lang: str = "") -> tuple[str, int, str]:
    """
    Parse a transcribed voice command and extract surf forecast parameters.

    Parameters
    ----------
    text : str
        Transcribed voice text (Hebrew or English).
    lang : str
        Language hint from the transcription engine (e.g. "he", "en").
        If empty or unreliable, language is auto-detected from the text.

    Returns
    -------
    beach : str
        Canonical beach name (matches a key in surf_tools.BEACH_COORDS).
    days : int
        Forecast duration in days.
    lang : str
        Detected / confirmed language code ("he" or "en").
    """
    normalised = text.strip().lower()

    # --- Language -----------------------------------------------------------
    detected_lang = _detect_language(normalised)
    # Prefer the explicit hint when it agrees with content; fall back to
    # content-based detection when the hint is missing or mismatched.
    resolved_lang = lang if lang in ("he", "en") else detected_lang
    # Content always wins for Hebrew (Whisper sometimes returns "en" for
    # mixed-language audio).
    if detected_lang == "he":
        resolved_lang = "he"

    # --- Beach --------------------------------------------------------------
    beach = _extract_beach(normalised)

    # --- Duration -----------------------------------------------------------
    days = _extract_days(normalised)

    return beach, days, resolved_lang


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _extract_beach(text: str) -> str:
    """
    Return the canonical beach name found in *text*, or the default
    ("habonim") when nothing is recognised.

    Multi-word aliases are checked before single-word ones so that
    "tel aviv" is matched before a hypothetical single-word alias.
    """
    # Sort aliases longest-first to prefer multi-word matches
    for alias in sorted(BEACH_ALIASES, key=len, reverse=True):
        if alias in text:
            return BEACH_ALIASES[alias]
    return "habonim"


def _extract_days(text: str) -> int:
    """
    Return the number of forecast days implied by *text*, or 7 (default)
    when no duration keyword is found.

    Patterns are evaluated in declaration order; the first match wins.
    """
    for pattern, days in DURATION_PATTERNS:
        if pattern.search(text):
            return days
    return 7
