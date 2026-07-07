"""
app/preprocessing/normalizers/roman_numeral_normalizer.py
==========================================================
Stage 12 — Roman numeral verbalization.

Converts uppercase Roman numerals to cardinal English words.
Only matches unambiguous standalone Roman numerals (bounded by word
boundaries, preceded by a contextual hint like "Chapter", "Part",
"Section", "Volume", "Act", "Scene", "Phase", "Stage", or uppercase-only).

  Chapter IV    → "Chapter four"
  Part III      → "Part three"
  Act II Scene I → "Act two Scene one"

Does NOT convert ambiguous single letters like "I", "V", "X" in
ordinary text (would mangle too much). Requires a context word prefix
OR the numeral to be multi-character.
"""

from __future__ import annotations

import re

from app.core.logger import get_logger
from app.preprocessing.normalizers.number_normalizer import indian_int_to_words

log = get_logger(__name__)

# Roman numeral value table
_ROMAN_VALUES = [
    ("M", 1000), ("CM", 900), ("D", 500), ("CD", 400),
    ("C", 100), ("XC", 90), ("L", 50), ("XL", 40),
    ("X", 10), ("IX", 9), ("V", 5), ("IV", 4), ("I", 1),
]


def _roman_to_int(roman: str) -> int | None:
    """Convert a Roman numeral string to integer. Returns None if invalid."""
    if not roman:
        return None
    i = 0
    result = 0
    roman = roman.upper()
    for symbol, value in _ROMAN_VALUES:
        while roman[i:i + len(symbol)] == symbol:
            result += value
            i += len(symbol)
    if i != len(roman):
        return None  # leftover characters — invalid
    return result if result > 0 else None


# Context words that legitimately precede Roman numerals
_CONTEXT_WORDS = (
    "chapter", "part", "section", "volume", "act", "scene",
    "phase", "stage", "article", "clause", "rule", "appendix",
    "annex", "figure", "table", "item", "book", "unit", "lesson",
)
_CONTEXT_PAT = "(?:" + "|".join(_CONTEXT_WORDS) + r")\s+"

# Roman numeral pattern: multi-char (II, III, IV …) or single after context
_ROMAN_NUM_PAT = r"M{0,3}(?:CM|CD|D?C{0,3})(?:XC|XL|L?X{0,3})(?:IX|IV|V?I{0,3})"

_ROMAN_WITH_CONTEXT = re.compile(
    r"(?i)(" + _CONTEXT_PAT + r")" +   # context word(s)
    r"\b(" + _ROMAN_NUM_PAT + r")\b",  # Roman numeral
)

# Multi-char Roman numerals standalone (no context needed — must be ≥2 chars)
_ROMAN_STANDALONE = re.compile(
    r"\b(II|III|IV|VI|VII|VIII|IX|XI|XII|XIII|XIV|XV|XVI|XVII|XVIII|XIX|XX"
    r"|XXI|XXII|XXIII|XXIV|XXV|XXVI|XXVII|XXVIII|XXIX|XXX"
    r"|XL|L|LX|LXX|LXXX|XC|C|CL|CC|CCL|CCC|CD|D|DC|DCC|DCCC|CM|M)\b"
)


class RomanNumeralNormalizer:
    """Stage 12: Convert Roman numerals to cardinal English words."""

    def normalize(self, text: str, lang: str = "hi") -> str:
        # Context-prefixed first (most reliable)
        def _replace_with_context(m: re.Match) -> str:
            context = m.group(1)
            roman = m.group(2)
            n = _roman_to_int(roman)
            if n is None:
                return m.group(0)
            return context + indian_int_to_words(n)

        text = _ROMAN_WITH_CONTEXT.sub(_replace_with_context, text)

        # Then unambiguous multi-char standalone
        def _replace_standalone(m: re.Match) -> str:
            n = _roman_to_int(m.group(0))
            if n is None:
                return m.group(0)
            return indian_int_to_words(n)

        text = _ROMAN_STANDALONE.sub(_replace_standalone, text)
        return text
