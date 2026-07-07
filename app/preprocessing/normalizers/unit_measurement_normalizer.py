"""
app/preprocessing/normalizers/unit_measurement_normalizer.py
=============================================================
Stage 11 — Unit and measurement verbalization.

  10km  → "ten kilometers"
  5kg   → "five kilograms"
  100ml → "one hundred milliliters"
  30°C  → "thirty degrees celsius"
  6ft   → "six feet"
  72in  → "seventy two inches"
  500m  → "five hundred meters"
  1.5L  → "one point five liters"

Handles both concatenated (10km) and spaced (10 km) forms.
Case-sensitive for some units (mL vs ml).
"""

from __future__ import annotations

import re

from app.core.logger import get_logger
from app.preprocessing.normalizers.number_normalizer import indian_int_to_words

log = get_logger(__name__)

# ── Unit table: pattern → spoken form (singular assumed; plural handled below) ─
# Ordered longest-first to avoid prefix shadowing (mm before m, etc.)

_UNITS: list[tuple[str, str, str]] = [
    # Distance
    ("km", "kilometer", "kilometers"),
    ("cm", "centimeter", "centimeters"),
    ("mm", "millimeter", "millimeters"),
    ("nm", "nanometer", "nanometers"),
    ("mi", "mile", "miles"),
    ("ft", "foot", "feet"),
    ("in", "inch", "inches"),
    ("yd", "yard", "yards"),
    ("m", "meter", "meters"),
    # Weight
    ("kg", "kilogram", "kilograms"),
    ("mg", "milligram", "milligrams"),
    ("g", "gram", "grams"),
    ("lb", "pound", "pounds"),
    ("oz", "ounce", "ounces"),
    ("t", "tonne", "tonnes"),
    # Volume
    ("ml", "milliliter", "milliliters"),
    ("mL", "milliliter", "milliliters"),
    ("cl", "centiliter", "centiliters"),
    ("dl", "deciliter", "deciliters"),
    ("L", "liter", "liters"),
    ("l", "liter", "liters"),
    # Temperature
    ("°C", "degree celsius", "degrees celsius"),
    ("°F", "degree fahrenheit", "degrees fahrenheit"),
    ("K", "kelvin", "kelvin"),
    # Speed
    ("kmph", "kilometer per hour", "kilometers per hour"),
    ("kph", "kilometer per hour", "kilometers per hour"),
    ("mph", "mile per hour", "miles per hour"),
    # Data
    ("GB", "gigabyte", "gigabytes"),
    ("MB", "megabyte", "megabytes"),
    ("KB", "kilobyte", "kilobytes"),
    ("TB", "terabyte", "terabytes"),
    ("GHz", "gigahertz", "gigahertz"),
    ("MHz", "megahertz", "megahertz"),
    ("kHz", "kilohertz", "kilohertz"),
    ("Hz", "hertz", "hertz"),
    # Power/Energy
    ("kW", "kilowatt", "kilowatts"),
    ("MW", "megawatt", "megawatts"),
    ("kWh", "kilowatt hour", "kilowatt hours"),
    ("W", "watt", "watts"),
    ("V", "volt", "volts"),
    ("A", "ampere", "amperes"),
]

# Build regex: number + optional space + unit, word-boundary aware
# Sort by length of unit pattern (longest first) to avoid prefix clashes
_SORTED_UNITS = sorted(_UNITS, key=lambda x: len(x[0]), reverse=True)

_UNIT_PATTERN = "|".join(re.escape(u[0]) for u in _SORTED_UNITS)
_UNIT_LOOKUP = {u[0]: (u[1], u[2]) for u in _SORTED_UNITS}

_MEASURE_RE = re.compile(
    r"(-?\d+(?:\.\d+)?)\s*(" + _UNIT_PATTERN + r")\b"
)

_DIGIT_WORDS = ["zero","one","two","three","four","five","six","seven","eight","nine"]


def _num_to_words(raw: str) -> str:
    if "." in raw:
        neg = raw.startswith("-")
        abs_raw = raw.lstrip("-")
        int_p, dec_p = abs_raw.split(".", 1)
        iw = indian_int_to_words(int(int_p))
        dw = " ".join(_DIGIT_WORDS[int(d)] for d in dec_p)
        result = f"{iw} point {dw}"
        return ("minus " + result) if neg else result
    n = int(raw)
    return ("minus " + indian_int_to_words(-n)) if n < 0 else indian_int_to_words(n)


class UnitMeasurementNormalizer:
    """Stage 11: Verbalize measurement quantities with units."""

    def normalize(self, text: str, lang: str = "hi") -> str:
        def _replace(m: re.Match) -> str:
            try:
                num_str = m.group(1)
                unit_str = m.group(2)
                num_words = _num_to_words(num_str)
                singular, plural = _UNIT_LOOKUP.get(unit_str, (unit_str, unit_str))
                # Use plural unless number is exactly 1
                unit_words = singular if num_str.lstrip("-") in ("1", "1.0") else plural
                return f"{num_words} {unit_words}"
            except Exception:  # noqa: BLE001
                return m.group(0)

        return _MEASURE_RE.sub(_replace, text)
