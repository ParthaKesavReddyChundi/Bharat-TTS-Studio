"""
app/preprocessing/normalizers/date_time_normalizer.py
======================================================
Stage 5 — Date and time verbalization.

Handles dates:
  - DD/MM/YYYY  →  "twenty third May two thousand twenty six"
  - DD-MM-YYYY, DD.MM.YYYY
  - Month DD, YYYY  →  "May twenty third two thousand twenty six"
  - DD Month YYYY
  - YYYY-MM-DD (ISO 8601)

Handles times:
  - 10:45 AM  →  "ten forty five AM"
  - 14:30     →  "two thirty PM"
  - 10:45:00  →  "ten forty five"

Rule: runs BEFORE number normalizer so date digits are consumed first.
"""

from __future__ import annotations

import re

from app.core.logger import get_logger
from app.preprocessing.normalizers.number_normalizer import (
    _below_hundred,
    _below_thousand,
    indian_int_to_words,
)

log = get_logger(__name__)

# ── Month tables ──────────────────────────────────────────────────────────────

_MONTHS_FULL = [
    "", "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]
_MONTHS_SHORT = [
    "", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
]
_MONTH_NAME_TO_NUM: dict[str, int] = {}
for _i, _m in enumerate(_MONTHS_FULL[1:], 1):
    _MONTH_NAME_TO_NUM[_m.lower()] = _i
    _MONTH_NAME_TO_NUM[_MONTHS_SHORT[_i].lower()] = _i

_ORDINAL_DAYS = [
    "", "first", "second", "third", "fourth", "fifth", "sixth", "seventh",
    "eighth", "ninth", "tenth", "eleventh", "twelfth", "thirteenth",
    "fourteenth", "fifteenth", "sixteenth", "seventeenth", "eighteenth",
    "nineteenth", "twentieth", "twenty first", "twenty second", "twenty third",
    "twenty fourth", "twenty fifth", "twenty sixth", "twenty seventh",
    "twenty eighth", "twenty ninth", "thirtieth", "thirty first",
]


def _year_to_words(year: int) -> str:
    """Convert a 4-digit year to spoken form."""
    if year < 1 or year > 9999:
        return str(year)
    # Prefer century-style for common years: 1999 → "nineteen ninety nine"
    century = year // 100
    remainder = year % 100
    if 1000 <= year <= 1999:
        c_words = _below_hundred(century)
        r_words = "oh " + _below_hundred(remainder) if 1 <= remainder <= 9 else _below_hundred(remainder)
        return c_words + (" " + r_words if remainder else " hundred")
    if 2000 <= year <= 2099:
        if remainder == 0:
            return "two thousand"
        return "two thousand " + _below_hundred(remainder)
    # fallback: standard integer
    return indian_int_to_words(year)


def _day_to_words(day: int) -> str:
    if 1 <= day <= 31:
        return _ORDINAL_DAYS[day]
    return str(day)


def _month_num_to_name(m: int) -> str:
    if 1 <= m <= 12:
        return _MONTHS_FULL[m]
    return str(m)


# ── Date patterns ─────────────────────────────────────────────────────────────

_MONTH_NAMES_PAT = "|".join(
    list(_MONTHS_FULL[1:]) + list(_MONTHS_SHORT[1:])
)

# DD/MM/YYYY, DD-MM-YYYY, DD.MM.YYYY
_DMY_RE = re.compile(
    r"\b(0?[1-9]|[12]\d|3[01])"    # day
    r"([\/\-\.])"                    # separator
    r"(0?[1-9]|1[0-2])"             # month
    r"\2"                            # same separator
    r"(\d{4})\b",                    # year
)

# YYYY-MM-DD (ISO)
_ISO_RE = re.compile(
    r"\b(\d{4})-(0?[1-9]|1[0-2])-(0?[1-9]|[12]\d|3[01])\b"
)

# DD Month YYYY or Month DD, YYYY
_TEXT_DATE_RE = re.compile(
    r"\b"
    r"(?:"
    r"(0?[1-9]|[12]\d|3[01])\s+(" + _MONTH_NAMES_PAT + r")\s+(\d{4})"  # DD Month YYYY
    r"|"
    r"(" + _MONTH_NAMES_PAT + r")\s+(0?[1-9]|[12]\d|3[01]),?\s+(\d{4})"  # Month DD, YYYY
    r")"
    r"\b",
    re.IGNORECASE,
)

# Time: HH:MM (AM/PM optional), HH:MM:SS
_TIME_RE = re.compile(
    r"\b([01]?\d|2[0-3]):([0-5]\d)(?::[0-5]\d)?\s*(AM|PM|am|pm)?\b"
)


class DateTimeNormalizer:
    """Stage 5: Verbalize dates and times."""

    def normalize(self, text: str, lang: str = "hi") -> str:
        # Order matters: text dates first (more specific), then numeric
        text = _TEXT_DATE_RE.sub(self._replace_text_date, text)
        text = _ISO_RE.sub(self._replace_iso, text)
        text = _DMY_RE.sub(self._replace_dmy, text)
        text = _TIME_RE.sub(self._replace_time, text)
        return text

    def _replace_dmy(self, m: re.Match) -> str:
        try:
            day, _, month, year = int(m.group(1)), m.group(2), int(m.group(3)), int(m.group(4))
            return f"{_day_to_words(day)} {_month_num_to_name(month)} {_year_to_words(year)}"
        except Exception:  # noqa: BLE001
            return m.group(0)

    def _replace_iso(self, m: re.Match) -> str:
        try:
            year, month, day = int(m.group(1)), int(m.group(2)), int(m.group(3))
            return f"{_day_to_words(day)} {_month_num_to_name(month)} {_year_to_words(year)}"
        except Exception:  # noqa: BLE001
            return m.group(0)

    def _replace_text_date(self, m: re.Match) -> str:
        try:
            if m.group(1):  # DD Month YYYY
                day, month_name, year = int(m.group(1)), m.group(2), int(m.group(3))
            else:           # Month DD, YYYY
                month_name, day, year = m.group(4), int(m.group(5)), int(m.group(6))
            month_num = _MONTH_NAME_TO_NUM.get(month_name.lower(), 0)
            month_str = _month_num_to_name(month_num) if month_num else month_name
            return f"{_day_to_words(day)} {month_str} {_year_to_words(year)}"
        except Exception:  # noqa: BLE001
            return m.group(0)

    def _replace_time(self, m: re.Match) -> str:
        try:
            hour = int(m.group(1))
            minute = int(m.group(2))
            ampm = m.group(3) or ""

            # Convert 24h to 12h if no AM/PM given
            if not ampm and hour >= 12:
                ampm = "PM"
                if hour > 12:
                    hour -= 12
            elif not ampm and hour == 0:
                hour = 12
                ampm = "AM"

            hour_words = _below_hundred(hour)
            if minute == 0:
                time_words = f"{hour_words} o'clock"
            elif minute < 10:
                time_words = f"{hour_words} oh {_below_hundred(minute)}"
            else:
                time_words = f"{hour_words} {_below_hundred(minute)}"

            if ampm:
                time_words += " " + ampm.upper()
            return time_words
        except Exception:  # noqa: BLE001
            return m.group(0)
