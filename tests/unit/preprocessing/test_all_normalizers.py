"""
tests/unit/preprocessing/test_all_normalizers.py
==================================================
Comprehensive table-driven tests for all 15 pipeline normalizers.
One test class per normalizer, one parametrized test method per class.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[3]))

import pytest

# ── 1. UnicodeNormalizer ──────────────────────────────────────────────────────
from app.preprocessing.normalizers.unicode_normalizer import UnicodeNormalizer

class TestUnicodeNormalizer:
    @pytest.fixture
    def n(self): return UnicodeNormalizer()

    @pytest.mark.parametrize("text,expected", [
        ("hello", "hello"),
        ("नमस्ते", "नमस्ते"),          # Devanagari passthrough
        ("café", "café"),              # NFC passthrough
        ("hello\x00world", "helloworld"),   # null byte stripped
        ("text\x01with\x02ctrl", "textwithctrl"),
        ("tabs\there", "tabs\there"),  # tab preserved
        ("line\nbreak", "line\nbreak"),
        ("soft\u00adhyphen", "softhyphen"),   # soft hyphen stripped
        ("zwnj\u200c here", "zwnj\u200c here"),  # ZWNJ preserved
        ("", ""),
    ])
    def test_normalize(self, n, text, expected):
        assert n.normalize(text) == expected


# ── 2. EmojiHandler ──────────────────────────────────────────────────────────
from app.preprocessing.normalizers.emoji_handler import EmojiHandler

class TestEmojiHandler:
    @pytest.fixture
    def strip(self): return EmojiHandler(mode="strip")
    @pytest.fixture
    def verbalize(self): return EmojiHandler(mode="verbalize")

    @pytest.mark.parametrize("text,expected", [
        ("Hello 😊 world", "Hello  world"),
        ("No emoji here", "No emoji here"),
        ("Multi 🎉🎊 emojis", "Multi  emojis"),
        ("", ""),
    ])
    def test_strip(self, strip, text, expected):
        assert strip.normalize(text) == expected

    def test_verbalize_returns_something(self, verbalize):
        result = verbalize.normalize("Hello 😊")
        assert "Hello" in result
        assert "😊" not in result


# ── 3. ContactPatternNormalizer ───────────────────────────────────────────────
from app.preprocessing.normalizers.contact_pattern_normalizer import ContactPatternNormalizer

class TestContactPatternNormalizer:
    @pytest.fixture
    def n(self): return ContactPatternNormalizer()

    @pytest.mark.parametrize("text,expected_contains", [
        ("user@example.com", ["at", "example", "dot", "com"]),
        ("https://example.com", ["example", "dot", "com"]),
        ("#trending topic", ["hashtag trending"]),
        ("@username replied", ["at username"]),
    ])
    def test_contact(self, n, text, expected_contains):
        result = n.normalize(text)
        for part in expected_contains:
            assert part in result, f"Expected '{part}' in '{result}'"


# ── 4. AbbreviationExpander ───────────────────────────────────────────────────
from app.preprocessing.normalizers.abbreviation_expander import AbbreviationExpander

class TestAbbreviationExpander:
    @pytest.fixture
    def n(self): return AbbreviationExpander()

    @pytest.mark.parametrize("text,expected_contains", [
        ("Dr. Smith", ["doctor"]),
        ("Mr. Kumar", ["mister"]),
        ("Prof. Rao", ["professor"]),
        ("Ltd. Company", ["limited"]),
        ("etc. more", ["et cetera"]),
        ("Pvt. Ltd.", ["private", "limited"]),
    ])
    def test_expand(self, n, text, expected_contains):
        result = n.normalize(text, lang="hi").lower()
        for part in expected_contains:
            assert part in result, f"Expected '{part}' in '{result}'"


# ── 5. DateTimeNormalizer ─────────────────────────────────────────────────────
from app.preprocessing.normalizers.date_time_normalizer import DateTimeNormalizer

class TestDateTimeNormalizer:
    @pytest.fixture
    def n(self): return DateTimeNormalizer()

    @pytest.mark.parametrize("text,expected_contains", [
        ("23/05/2026", ["twenty third", "May", "two thousand twenty six"]),
        ("01/01/2000", ["first", "January", "two thousand"]),
        ("2026-05-23", ["twenty third", "May"]),
        ("May 23, 2026", ["twenty third", "May"]),
        ("10:45 AM", ["ten", "forty five", "AM"]),
        ("14:30", ["two", "thirty", "PM"]),
        ("09:00 AM", ["nine", "o'clock", "AM"]),
    ])
    def test_datetime(self, n, text, expected_contains):
        result = n.normalize(text)
        for part in expected_contains:
            assert part in result, f"Expected '{part}' in '{result}'"


# ── 6. CurrencyNormalizer ─────────────────────────────────────────────────────
from app.preprocessing.normalizers.currency_normalizer import CurrencyNormalizer

class TestCurrencyNormalizer:
    @pytest.fixture
    def n(self): return CurrencyNormalizer()

    @pytest.mark.parametrize("text,expected_contains", [
        ("₹2500",              ["two thousand five hundred", "rupees"]),
        ("₹2,50,000",          ["two lakh fifty thousand", "rupees"]),
        ("₹10.50",             ["ten", "rupees", "fifty", "paise"]),
        ("Rs.100",             ["one hundred", "rupees"]),
        ("INR 5000",           ["five thousand", "rupees"]),
        ("$100",               ["one hundred", "dollars"]),
        ("€50",                ["fifty", "euros"]),
        ("£30",                ["thirty", "pounds"]),
        ("₹1,00,00,000",       ["one crore", "rupees"]),
    ])
    def test_currency(self, n, text, expected_contains):
        result = n.normalize(text)
        for part in expected_contains:
            assert part in result, f"Expected '{part}' in '{result}'"


# ── 7. OrdinalNormalizer ─────────────────────────────────────────────────────
from app.preprocessing.normalizers.ordinal_normalizer import OrdinalNormalizer

class TestOrdinalNormalizer:
    @pytest.fixture
    def n(self): return OrdinalNormalizer()

    @pytest.mark.parametrize("text,expected", [
        ("1st place",    "first place"),
        ("2nd attempt",  "second attempt"),
        ("3rd floor",    "third floor"),
        ("4th row",      "fourth row"),
        ("11th edition", "eleventh edition"),
        ("21st century", "twenty first century"),
        ("23rd May",     "twenty third May"),
        ("100th run",    "one hundredth run"),
    ])
    def test_ordinal(self, n, text, expected):
        assert n.normalize(text) == expected


# ── 8. FractionScientificNormalizer ──────────────────────────────────────────
from app.preprocessing.normalizers.fraction_scientific_normalizer import FractionScientificNormalizer

class TestFractionScientific:
    @pytest.fixture
    def n(self): return FractionScientificNormalizer()

    @pytest.mark.parametrize("text,expected_contains", [
        ("3/4 cup",     ["three", "fourths"]),
        ("1/2 price",   ["one", "half"]),
        ("3.14 value",  ["three", "point", "one", "four"]),
        ("0.5 kg",      ["zero", "point", "five"]),
        ("1.2e3 Hz",    ["one", "point", "two", "times ten to the power", "three"]),
        ("2E-6 seconds",["two", "times ten to the power minus", "six"]),
    ])
    def test_fraction(self, n, text, expected_contains):
        result = n.normalize(text)
        for part in expected_contains:
            assert part in result, f"Expected '{part}' in '{result}'"


# ── 9. PercentageNormalizer ───────────────────────────────────────────────────
from app.preprocessing.normalizers.percentage_normalizer import PercentageNormalizer

class TestPercentageNormalizer:
    @pytest.fixture
    def n(self): return PercentageNormalizer()

    @pytest.mark.parametrize("text,expected", [
        ("50% complete",   "fifty percent complete"),
        ("100% done",      "one hundred percent done"),
        ("3.5% growth",    "three point five percent growth"),
        ("-2.5% decline",  "minus two point five percent decline"),
    ])
    def test_percent(self, n, text, expected):
        assert n.normalize(text) == expected


# ── 10. UnitMeasurementNormalizer ────────────────────────────────────────────
from app.preprocessing.normalizers.unit_measurement_normalizer import UnitMeasurementNormalizer

class TestUnitNormalizer:
    @pytest.fixture
    def n(self): return UnitMeasurementNormalizer()

    @pytest.mark.parametrize("text,expected_contains", [
        ("10km distance",   ["ten", "kilometers"]),
        ("5kg weight",      ["five", "kilograms"]),
        ("100ml water",     ["one hundred", "milliliters"]),
        ("30°C temp",       ["thirty", "degrees celsius"]),
        ("6ft tall",        ["six", "feet"]),
        ("1.5L bottle",     ["one point five", "liters"]),
        ("500MB file",      ["five hundred", "megabytes"]),
    ])
    def test_units(self, n, text, expected_contains):
        result = n.normalize(text)
        for part in expected_contains:
            assert part in result, f"Expected '{part}' in '{result}'"


# ── 11. RomanNumeralNormalizer ────────────────────────────────────────────────
from app.preprocessing.normalizers.roman_numeral_normalizer import RomanNumeralNormalizer

class TestRomanNumeralNormalizer:
    @pytest.fixture
    def n(self): return RomanNumeralNormalizer()

    @pytest.mark.parametrize("text,expected_contains", [
        ("Chapter IV",     ["Chapter", "four"]),
        ("Part III",       ["Part", "three"]),
        ("Act II Scene I", ["two", "one"]),
        ("Section XII",    ["twelve"]),
        ("Volume IX",      ["nine"]),
    ])
    def test_roman(self, n, text, expected_contains):
        result = n.normalize(text)
        for part in expected_contains:
            assert part in result, f"Expected '{part}' in '{result}'"


# ── 12. PincodeVehicleNormalizer ──────────────────────────────────────────────
from app.preprocessing.normalizers.pincode_vehicle_normalizer import PincodeVehicleNormalizer

class TestPincodeVehicle:
    @pytest.fixture
    def n(self): return PincodeVehicleNormalizer()

    @pytest.mark.parametrize("text,expected_contains", [
        ("PIN: 560001",            ["five six zero zero zero one"]),
        ("Pincode 110011",         ["one one zero zero one one"]),
        ("vehicle KA-01-AB-1234",  ["K A", "zero one", "A B", "one two three four"]),
    ])
    def test_pincode_vehicle(self, n, text, expected_contains):
        result = n.normalize(text)
        for part in expected_contains:
            assert part in result, f"Expected '{part}' in '{result}'"


# ── 13. CodeMixSegmenter ─────────────────────────────────────────────────────
from app.preprocessing.normalizers.code_mix_segmenter import CodeMixSegmenter

class TestCodeMixSegmenter:
    @pytest.fixture
    def n(self): return CodeMixSegmenter()

    def test_pure_hindi(self, n):
        spans = n.segment("नमस्ते दुनिया", lang="hi")
        langs = [s[1] for s in spans]
        assert "hi" in langs

    def test_pure_english(self, n):
        spans = n.segment("hello world", lang="en")
        langs = [s[1] for s in spans]
        assert "en" in langs

    def test_code_mixed(self, n):
        spans = n.segment("hello नमस्ते world", lang="hi")
        # Should have at least 2 different lang tags
        langs = {s[1] for s in spans}
        assert len(langs) >= 2

    def test_text_unchanged(self, n):
        text = "hello नमस्ते"
        assert n.normalize(text) == text


# ── 14. PunctuationCleaner ────────────────────────────────────────────────────
from app.preprocessing.normalizers.punctuation_cleaner import PunctuationCleaner

class TestPunctuationCleaner:
    @pytest.fixture
    def n(self): return PunctuationCleaner()

    @pytest.mark.parametrize("text,expected", [
        ("Hello!!!",              "Hello!"),
        ("Really???",             "Really?"),
        ("Wait...",               "Wait, "),   # ellipsis → comma+space (stripped at end)
        ("He said \u201chello\u201d", 'He said "hello"'),
        ("a\u2014b",             "a - b"),
        ("a\u2013b",             "a - b"),
        ("  extra   spaces  ",   "extra spaces"),
        ("pipe|caret^back\\tick", "pipe caret back tick"),
    ])
    def test_punct(self, n, text, expected):
        result = n.normalize(text).strip()
        assert result == expected.strip(), f"Got '{result}', expected '{expected.strip()}'"
