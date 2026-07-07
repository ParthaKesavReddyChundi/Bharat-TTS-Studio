"""
app/preprocessing/normalizers/ordinal_normalizer.py
====================================================
Stage 8 — Ordinal number verbalization.

Converts:
  1st → "first"    2nd → "second"    3rd → "third"
  4th → "fourth"   11th → "eleventh" 21st → "twenty first"
  100th → "one hundredth"

Rule: runs AFTER DateTimeNormalizer (so date days aren't double-processed)
and AFTER NumberNormalizer (so base numbers are already spoken).

Actually runs BEFORE NumberNormalizer in the pipeline so that "1st" is
consumed as an ordinal rather than "1" becoming "one" + stray "st".
"""

from __future__ import annotations

import re

from app.core.logger import get_logger
from app.preprocessing.normalizers.number_normalizer import indian_int_to_words

log = get_logger(__name__)

# ── Ordinal suffix → spoken form mapping for common irregulars ────────────────

_ORDINAL_IRREGULAR: dict[int, str] = {
    1: "first", 2: "second", 3: "third", 4: "fourth", 5: "fifth",
    6: "sixth", 7: "seventh", 8: "eighth", 9: "ninth", 10: "tenth",
    11: "eleventh", 12: "twelfth", 13: "thirteenth", 14: "fourteenth",
    15: "fifteenth", 16: "sixteenth", 17: "seventeenth", 18: "eighteenth",
    19: "nineteenth", 20: "twentieth",
    21: "twenty first", 22: "twenty second", 23: "twenty third",
    24: "twenty fourth", 25: "twenty fifth", 26: "twenty sixth",
    27: "twenty seventh", 28: "twenty eighth", 29: "twenty ninth",
    30: "thirtieth", 31: "thirty first",
}

# Suffix for numbers not in the irregular table
_ORDINAL_SUFFIX = {
    1: "st", 2: "nd", 3: "rd",
}


def _cardinal_to_ordinal_words(n: int) -> str:
    """Convert a positive integer to its ordinal words."""
    if n in _ORDINAL_IRREGULAR:
        return _ORDINAL_IRREGULAR[n]
    # For larger numbers: base words + "th" approximation
    base = indian_int_to_words(n)
    # Replace last word with ordinal form
    _ENDS_TO_ORDINAL = {
        "one": "first", "two": "second", "three": "third", "four": "fourth",
        "five": "fifth", "six": "sixth", "seven": "seventh", "eight": "eighth",
        "nine": "ninth", "ten": "tenth", "eleven": "eleventh", "twelve": "twelfth",
        "twenty": "twentieth", "thirty": "thirtieth", "forty": "fortieth",
        "fifty": "fiftieth", "sixty": "sixtieth", "seventy": "seventieth",
        "eighty": "eightieth", "ninety": "ninetieth",
        "hundred": "hundredth", "thousand": "thousandth",
        "lakh": "lakhth", "crore": "croreth",
    }
    words = base.split()
    last = words[-1]
    words[-1] = _ENDS_TO_ORDINAL.get(last, last + "th")
    return " ".join(words)


# Matches e.g. 1st, 2nd, 3rd, 4th, 21st, 100th (not inside larger numbers)
_ORDINAL_RE = re.compile(
    r"\b(\d+)(st|nd|rd|th)\b",
    re.IGNORECASE,
)


class OrdinalNormalizer:
    """Stage 8: Convert ordinal numbers (1st, 2nd …) to spoken words."""

    def normalize(self, text: str, lang: str = "hi") -> str:
        def _replace(m: re.Match) -> str:
            try:
                n = int(m.group(1))
                suffix = m.group(2).lower()
                # Validate suffix matches number
                expected_suffix = (
                    "st" if n % 10 == 1 and n % 100 != 11 else
                    "nd" if n % 10 == 2 and n % 100 != 12 else
                    "rd" if n % 10 == 3 and n % 100 != 13 else
                    "th"
                )
                if suffix not in ("st", "nd", "rd", "th"):
                    return m.group(0)
                return _cardinal_to_ordinal_words(n)
            except Exception:  # noqa: BLE001
                return m.group(0)

        return _ORDINAL_RE.sub(_replace, text)
