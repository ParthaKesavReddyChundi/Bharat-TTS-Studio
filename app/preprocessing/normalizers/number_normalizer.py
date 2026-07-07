"""
app/preprocessing/normalizers/number_normalizer.py
===================================================
Stage 7 — Number verbalization using the Indian numbering system.

Handles:
  - Plain integers: 300 → "three hundred"
  - Indian comma-formatted: 2,50,000 → "two lakh fifty thousand"
  - Western comma-formatted: 1,000,000 → "ten lakh" (auto-detected)
  - Decimal numbers: 3.14 → handled by FractionScientificNormalizer (skipped here)
  - Negative numbers: -5 → "minus five"
  - Standalone digits in text

Pipeline position: runs AFTER currency (so ₹ prefixed numbers are already gone)
and AFTER date/time (so date digits don't get re-processed).
"""

from __future__ import annotations

import re

from app.core.logger import get_logger

log = get_logger(__name__)

# ── Word tables ───────────────────────────────────────────────────────────────

_ONES = [
    "", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
    "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen",
    "seventeen", "eighteen", "nineteen",
]
_TENS = [
    "", "", "twenty", "thirty", "forty", "fifty",
    "sixty", "seventy", "eighty", "ninety",
]


# ── Core conversion ───────────────────────────────────────────────────────────

def _below_hundred(n: int) -> str:
    if n < 20:
        return _ONES[n]
    tens = _TENS[n // 10]
    ones = _ONES[n % 10]
    return tens if not ones else f"{tens} {ones}"


def _below_thousand(n: int) -> str:
    if n < 100:
        return _below_hundred(n)
    hundreds = _ONES[n // 100]
    rem = _below_hundred(n % 100)
    return f"{hundreds} hundred" if not rem else f"{hundreds} hundred {rem}"


def indian_int_to_words(n: int) -> str:
    """
    Convert a non-negative integer to English words using the Indian
    numbering system (lakh / crore).

    Args:
        n: Non-negative integer.

    Returns:
        English words e.g. "two lakh fifty thousand".
    """
    if n == 0:
        return "zero"

    parts: list[str] = []

    # Crores (10^7)
    if n >= 1_00_00_000:
        crore_part = n // 1_00_00_000
        parts.append(_below_thousand(crore_part) + " crore")
        n %= 1_00_00_000

    # Lakhs (10^5)
    if n >= 1_00_000:
        lakh_part = n // 1_00_000
        parts.append(_below_thousand(lakh_part) + " lakh")
        n %= 1_00_000

    # Thousands (10^3)
    if n >= 1_000:
        thou_part = n // 1_000
        parts.append(_below_thousand(thou_part) + " thousand")
        n %= 1_000

    if n > 0:
        parts.append(_below_thousand(n))

    return " ".join(parts)


def number_to_words(n: int) -> str:
    """
    Convert any integer (including negative) to words.

    Args:
        n: Integer (positive or negative).

    Returns:
        English words.
    """
    if n < 0:
        return "minus " + indian_int_to_words(-n)
    return indian_int_to_words(n)


def _parse_indian_number(text: str) -> int | None:
    """
    Parse an Indian-format comma-grouped number string to int.
    Accepts: "2,50,000" or "1,00,00,000" or "300".

    Returns:
        Parsed integer, or None if unparseable.
    """
    raw = text.replace(",", "")
    if raw.lstrip("-").isdigit():
        return int(raw)
    return None


# ── Regex ─────────────────────────────────────────────────────────────────────

# Matches integers with optional Indian or Western comma grouping
# Negative sign allowed; does NOT match decimals (those go to Fraction normalizer)
_NUMBER_RE = re.compile(
    r"(?<![\d.])"       # not preceded by digit or dot
    r"(-?)"             # optional minus
    r"("
    r"\d{1,2}(?:,\d{2})*(?:,\d{3})"  # Indian grouped: 2,50,000 / 1,00,00,000
    r"|"
    r"\d{1,3}(?:,\d{3})+"            # Western grouped: 1,000,000
    r"|"
    r"\d+"                            # plain integer
    r")"
    r"(?![\d.])"        # not followed by digit or dot
    r"(?![%₹$€£])",    # not followed by currency/percent (handled elsewhere)
    re.UNICODE,
)


class NumberNormalizer:
    """
    Stage 7: Replace numeric tokens with spoken English words (Indian system).
    """

    def normalize(self, text: str, lang: str = "hi") -> str:
        """
        Replace all standalone integers in *text* with spoken words.

        Args:
            text: Input string (already past currency / date normalizers).
            lang: BCP-47 language code (reserved for future Indic word forms).

        Returns:
            Text with numeric tokens replaced by words.
        """
        def _replace(m: re.Match) -> str:
            sign = m.group(1)
            digits = m.group(2)
            n = _parse_indian_number(digits)
            if n is None:
                return m.group(0)
            if sign == "-":
                n = -n
            try:
                return number_to_words(n)
            except Exception as exc:  # noqa: BLE001
                log.debug("NumberNormalizer: could not convert %r: %s", m.group(0), exc)
                return m.group(0)

        return _NUMBER_RE.sub(_replace, text)
