"""
app/preprocessing/normalizers/pincode_vehicle_normalizer.py
===========================================================
Stage 13 — Indian PIN codes and vehicle registration plates.

PIN codes:
  560001       → "five six zero zero zero one"
  PIN: 110011  → "PIN one one zero zero one one"
  Pincode 400001 → "Pincode four zero zero zero zero one"

Vehicle registration (Indian format):
  KA-01-AB-1234   → "K A zero one A B one two three four"
  MH12DE1433      → "M H one two D E one four three three"
  TN 01 AB 1234   → "T N zero one A B one two three four"

Distinguishes PIN codes from regular numbers by:
  - Exactly 6 digits
  - Preceded by PIN/Pincode/postal keyword, OR
  - Followed by a city/state context (best-effort)

Vehicle plates: Indian format with state code + district + series + number.
"""

from __future__ import annotations

import re

from app.core.logger import get_logger

log = get_logger(__name__)

_DIGIT_WORDS = ["zero","one","two","three","four","five","six","seven","eight","nine"]
_ALPHA_WORDS = {ch: ch.upper() for ch in "abcdefghijklmnopqrstuvwxyz"}


def _digits_to_words(digits: str) -> str:
    return " ".join(_DIGIT_WORDS[int(d)] for d in digits if d.isdigit())


def _char_to_spoken(ch: str) -> str:
    if ch.isdigit():
        return _DIGIT_WORDS[int(ch)]
    if ch.isalpha():
        return ch.upper()
    return ""


def _plate_to_words(plate: str) -> str:
    """Spell out each character of a vehicle plate."""
    parts = []
    # Split on separators, then spell out each segment
    segments = re.split(r"[\s\-]", plate)
    for seg in segments:
        spoken = " ".join(_char_to_spoken(c) for c in seg if c.isalnum())
        if spoken:
            parts.append(spoken)
    return " ".join(parts)


# PIN code with keyword context
_PINCODE_KEYWORD_RE = re.compile(
    r"\b(pin(?:code)?|postal(?:\s+code)?)\s*:?\s*(\d{6})\b",
    re.IGNORECASE,
)

# Vehicle plate: Indian format AA-NN-AA-NNNN or AANNMANNNN
_VEHICLE_RE = re.compile(
    r"\b"
    r"([A-Z]{2})"            # state code
    r"[\s\-]?"
    r"(\d{2})"               # district number
    r"[\s\-]?"
    r"([A-Z]{1,3})"          # series
    r"[\s\-]?"
    r"(\d{4})"               # registration number
    r"\b",
    re.IGNORECASE,
)

# Standalone 6-digit numbers that look like PIN codes (heuristic — only after
# common address keywords, or at start of certain contexts)
_ADDRESS_KEYWORDS = r"(address|city|state|location|area|district|tehsil|taluk|village|town|locality)\b[^.]{0,40}?"
_PINCODE_CONTEXT_RE = re.compile(
    r"(?i)(" + _ADDRESS_KEYWORDS + r")(\d{6})\b"
)


class PincodeVehicleNormalizer:
    """Stage 13: Spell out PIN codes and vehicle registration plates."""

    def normalize(self, text: str, lang: str = "hi") -> str:
        # PIN codes with explicit keywords (high confidence)
        def _pin_keyword(m: re.Match) -> str:
            keyword = m.group(1)
            digits = m.group(2)
            return f"{keyword} {_digits_to_words(digits)}"

        text = _PINCODE_KEYWORD_RE.sub(_pin_keyword, text)

        # PIN codes with context keywords
        def _pin_context(m: re.Match) -> str:
            context = m.group(1)
            digits = m.group(3)
            return f"{context}{_digits_to_words(digits)}"

        text = _PINCODE_CONTEXT_RE.sub(_pin_context, text)

        # Vehicle plates (before generic number normalizer would eat the digits)
        def _vehicle(m: re.Match) -> str:
            full = m.group(0)
            return _plate_to_words(full)

        text = _VEHICLE_RE.sub(_vehicle, text)
        return text

