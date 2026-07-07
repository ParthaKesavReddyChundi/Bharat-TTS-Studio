"""
tests/unit/preprocessing/test_number_normalizer.py
====================================================
Table-driven unit tests for NumberNormalizer (Stage 7)
and the core indian_int_to_words() function.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[3]))

import pytest
from app.preprocessing.normalizers.number_normalizer import (
    NumberNormalizer,
    indian_int_to_words,
    number_to_words,
)


# ── Core function tests ───────────────────────────────────────────────────────

@pytest.mark.parametrize("n,expected", [
    (0,           "zero"),
    (1,           "one"),
    (10,          "ten"),
    (11,          "eleven"),
    (19,          "nineteen"),
    (20,          "twenty"),
    (21,          "twenty one"),
    (99,          "ninety nine"),
    (100,         "one hundred"),
    (101,         "one hundred one"),
    (999,         "nine hundred ninety nine"),
    (1000,        "one thousand"),
    (1001,        "one thousand one"),
    (10000,       "ten thousand"),
    (99999,       "ninety nine thousand nine hundred ninety nine"),
    (100000,      "one lakh"),
    (250000,      "two lakh fifty thousand"),
    (1000000,     "ten lakh"),
    (10000000,    "one crore"),
    (10000001,    "one crore one"),
    (12500000,    "one crore twenty five lakh"),
    (100000000,   "ten crore"),
    (999999999,   "ninety nine crore ninety nine lakh ninety nine thousand nine hundred ninety nine"),
])
def test_indian_int_to_words(n, expected):
    assert indian_int_to_words(n) == expected


@pytest.mark.parametrize("n,expected", [
    (-1,    "minus one"),
    (-1000, "minus one thousand"),
    (0,     "zero"),
])
def test_number_to_words_negative(n, expected):
    assert number_to_words(n) == expected


# ── Normalizer integration tests ──────────────────────────────────────────────

@pytest.fixture
def normalizer():
    return NumberNormalizer()


@pytest.mark.parametrize("text,lang,expected", [
    # Plain integers
    ("I have 5 apples", "hi", "I have five apples"),
    ("300 people attended", "hi", "three hundred people attended"),
    # Indian comma format
    ("Population is 2,50,000", "hi", "Population is two lakh fifty thousand"),
    ("Budget is 1,00,00,000", "hi", "Budget is one crore"),
    # Western comma format
    ("Sales: 1,000 units", "hi", "Sales: one thousand units"),
    # Negative
    ("Temperature: -5 degrees", "hi", "Temperature: minus five degrees"),
    # Should NOT match decimals (those go to FractionScientific)
    ("Price is 3.14", "hi", "Price is 3.14"),
    # Should NOT match after % (handled by PercentageNormalizer)
    ("50% done", "hi", "50% done"),
])
def test_number_normalizer(normalizer, text, lang, expected):
    assert normalizer.normalize(text, lang) == expected
