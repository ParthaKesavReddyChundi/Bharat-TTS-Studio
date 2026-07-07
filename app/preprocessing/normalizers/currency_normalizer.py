"""
app/preprocessing/normalizers/currency_normalizer.py
=====================================================
Stage 6 — Currency verbalization.

Handles:
  - Indian Rupee: ₹2500 / Rs.2500 / INR 2500
  - US Dollar:    $100
  - Euro:         €50
  - British Pound: £30
  - Indian large amounts: ₹2,50,000 → "two lakh fifty thousand rupees"
  - Decimal amounts:      ₹10.50   → "ten rupees fifty paise"
  - No currency suffix: ₹2500 → "two thousand five hundred rupees"

Rule: currency normalization runs BEFORE generic number normalization so
that ₹-prefixed tokens aren't first mangled by the number rule.
"""

from __future__ import annotations

import re

from app.core.logger import get_logger
from app.preprocessing.normalizers.number_normalizer import (
    indian_int_to_words,
    _parse_indian_number,
)

log = get_logger(__name__)

# ── Currency symbol / prefix patterns ────────────────────────────────────────

_CURRENCY_RE = re.compile(
    r"(?:"
    r"(₹|Rs\.?|INR)\s*"           # Rupee prefix
    r"|(\$)\s*"                    # Dollar
    r"|(€)\s*"                     # Euro
    r"|(£)\s*"                     # Pound
    r")"
    r"(-?)"                        # optional minus
    r"(\d[\d,]*)"                  # integer part (with optional commas)
    r"(?:\.(\d{1,2}))?"           # optional .paise / .cents
    r"(?!\d)",                     # not followed by more digits
    re.UNICODE,
)


def _amount_to_words(
    integer_str: str,
    fraction_str: str | None,
    currency: str,
    fractional_unit: str,
) -> str:
    """Convert a parsed currency amount to spoken words."""
    n = _parse_indian_number(integer_str)
    if n is None:
        return f"{integer_str} {currency}"

    words = indian_int_to_words(n)
    result = f"{words} {currency}"

    if fraction_str:
        frac = int(fraction_str.ljust(2, "0")[:2])  # normalise to 2 digits
        if frac > 0:
            frac_words = indian_int_to_words(frac)
            result += f" {frac_words} {fractional_unit}"

    return result


class CurrencyNormalizer:
    """
    Stage 6: Replace currency tokens with spoken English words.
    """

    def normalize(self, text: str, lang: str = "hi") -> str:
        """
        Replace currency expressions in *text* with spoken words.

        Args:
            text: Input string.
            lang: BCP-47 language code (reserved for Indic word forms).

        Returns:
            Text with currency tokens replaced by words.
        """

        def _replace(m: re.Match) -> str:
            rupee_sym, dollar_sym, euro_sym, pound_sym = (
                m.group(1), m.group(2), m.group(3), m.group(4)
            )
            sign = m.group(5)
            integer_part = m.group(6)
            fraction_part = m.group(7)

            try:
                if rupee_sym:
                    result = _amount_to_words(integer_part, fraction_part, "rupees", "paise")
                elif dollar_sym:
                    result = _amount_to_words(integer_part, fraction_part, "dollars", "cents")
                elif euro_sym:
                    result = _amount_to_words(integer_part, fraction_part, "euros", "cents")
                elif pound_sym:
                    result = _amount_to_words(integer_part, fraction_part, "pounds", "pence")
                else:
                    return m.group(0)

                if sign == "-":
                    result = "minus " + result
                return result

            except Exception as exc:  # noqa: BLE001
                log.debug("CurrencyNormalizer: failed on %r: %s", m.group(0), exc)
                return m.group(0)

        return _CURRENCY_RE.sub(_replace, text)
