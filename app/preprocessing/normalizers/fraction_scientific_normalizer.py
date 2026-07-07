"""
app/preprocessing/normalizers/fraction_scientific_normalizer.py
================================================================
Stage 9 — Fractions, decimals, and scientific notation.

Handles:
  3/4          → "three fourths"
  1/2          → "one half"
  3.14         → "three point one four"
  0.5          → "zero point five"
  1.2e3        → "one point two times ten to the power three"
  1.5E-6       → "one point five times ten to the power minus six"
  2e10         → "two times ten to the power ten"

Does NOT handle integers (those go to NumberNormalizer).
"""

from __future__ import annotations

import re

from app.core.logger import get_logger
from app.preprocessing.normalizers.number_normalizer import (
    indian_int_to_words,
    _below_hundred,
)
from app.preprocessing.normalizers.ordinal_normalizer import _cardinal_to_ordinal_words

log = get_logger(__name__)

_DIGIT_WORDS = [
    "zero", "one", "two", "three", "four",
    "five", "six", "seven", "eight", "nine",
]

# Fraction denominators
_DENOMINATOR_WORDS: dict[int, tuple[str, str]] = {
    2: ("half", "halves"),
    3: ("third", "thirds"),
    4: ("fourth", "fourths"),
    5: ("fifth", "fifths"),
    6: ("sixth", "sixths"),
    7: ("seventh", "sevenths"),
    8: ("eighth", "eighths"),
    9: ("ninth", "ninths"),
    10: ("tenth", "tenths"),
}


def _decimal_digits_to_words(digits: str) -> str:
    """Spell out each digit after decimal point."""
    return " ".join(_DIGIT_WORDS[int(d)] for d in digits)


def _fraction_to_words(num: int, den: int) -> str:
    num_words = indian_int_to_words(num)
    if den in _DENOMINATOR_WORDS:
        singular, plural = _DENOMINATOR_WORDS[den]
        den_word = singular if num == 1 else plural
    else:
        den_word = _cardinal_to_ordinal_words(den) + ("s" if num != 1 else "")
    return f"{num_words} {den_word}"


# Scientific: 1.2e3 / 2E-6 / 3e10
_SCIENTIFIC_RE = re.compile(
    r"(-?\d+(?:\.\d+)?)[eE]([+-]?\d+)"
)

# Decimal: 3.14 (not matched if already consumed by scientific)
_DECIMAL_RE = re.compile(
    r"(?<!\d)(-?\d+)\.(\d+)(?!\d)"
)

# Simple fraction: 3/4 (not date separators — date already consumed)
_FRACTION_RE = re.compile(
    r"(?<!\d)(\d+)/(\d+)(?!\d)"
)


class FractionScientificNormalizer:
    """Stage 9: Verbalize fractions, decimals, and scientific notation."""

    def normalize(self, text: str, lang: str = "hi") -> str:
        # Order: scientific > decimal > fraction
        text = _SCIENTIFIC_RE.sub(self._replace_scientific, text)
        text = _DECIMAL_RE.sub(self._replace_decimal, text)
        text = _FRACTION_RE.sub(self._replace_fraction, text)
        return text

    def _replace_scientific(self, m: re.Match) -> str:
        try:
            base = m.group(1)
            exp = m.group(2)
            # Verbalize base
            if "." in base:
                int_part, dec_part = base.lstrip("-").split(".")
                base_words = indian_int_to_words(int(int_part)) + " point " + _decimal_digits_to_words(dec_part)
            else:
                base_words = indian_int_to_words(int(base))
            if base.startswith("-"):
                base_words = "minus " + base_words

            exp_int = int(exp)
            exp_words = indian_int_to_words(abs(exp_int))
            sign_word = "minus " if exp_int < 0 else ""
            return f"{base_words} times ten to the power {sign_word}{exp_words}"
        except Exception:  # noqa: BLE001
            return m.group(0)

    def _replace_decimal(self, m: re.Match) -> str:
        try:
            sign = "-" if m.group(1).startswith("-") else ""
            int_part = abs(int(m.group(1)))
            dec_part = m.group(2)
            int_words = indian_int_to_words(int_part)
            dec_words = _decimal_digits_to_words(dec_part)
            prefix = "minus " if sign else ""
            return f"{prefix}{int_words} point {dec_words}"
        except Exception:  # noqa: BLE001
            return m.group(0)

    def _replace_fraction(self, m: re.Match) -> str:
        try:
            num = int(m.group(1))
            den = int(m.group(2))
            if den == 0:
                return m.group(0)
            return _fraction_to_words(num, den)
        except Exception:  # noqa: BLE001
            return m.group(0)
