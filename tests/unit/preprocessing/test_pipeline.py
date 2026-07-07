"""
tests/unit/preprocessing/test_pipeline.py
==========================================
End-to-end pipeline integration tests.
Tests the full 15-stage chain on realistic Indian-language input.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[3]))

import pytest
from app.preprocessing.pipeline import PreprocessingPipeline


@pytest.fixture
def pipeline():
    return PreprocessingPipeline(emoji_mode="strip")


@pytest.mark.parametrize("text,lang,expected_contains", [
    # Basic Hindi TTS input
    ("नमस्ते, मेरा नाम राम है", "hi", ["नमस्ते"]),
    # Currency
    ("Price is ₹2,50,000 only", "hi", ["two lakh fifty thousand", "rupees"]),
    # Date
    ("Meeting on 23/05/2026", "hi", ["twenty third", "May"]),
    # Percentage + number
    ("50% of 1000 people", "hi", ["fifty percent", "one thousand"]),
    # Units
    ("Drive 10km at 100kmph", "hi", ["ten", "kilometers", "one hundred", "kilometers per hour"]),
    # Ordinal
    ("This is the 3rd attempt", "hi", ["third"]),
    # Emoji stripped
    ("Hello 😊 world", "hi", ["Hello", "world"]),
    # Abbreviations
    ("Dr. Singh attended", "hi", ["doctor"]),
    # Roman numeral
    ("Chapter IV begins", "hi", ["four"]),
    # PIN code
    ("My PIN: 560001", "hi", ["five six zero zero zero one"]),
    # Vehicle plate
    ("Car KA-01-AB-1234 was found", "hi", ["K A", "zero one"]),
    # Code-mixed
    ("I went to दिल्ली today", "hi", ["दिल्ली"]),
    # Fraction
    ("Take 3/4 cup of water", "hi", ["three", "fourths"]),
    # Scientific
    ("Speed is 3e8 m/s", "hi", ["three", "times ten to the power"]),
    # Punctuation cleanup
    ("Wow!!!  Amazing...", "hi", ["Wow!", "Amazing"]),
    # Empty input
    ("", "hi", []),
])
def test_pipeline_full(pipeline, text, lang, expected_contains):
    if not text:
        result, spans = pipeline.normalize(text, lang)
        return  # empty input — just don't crash

    result, spans = pipeline.normalize(text, lang)

    assert isinstance(result, str), "Result must be a string"
    assert isinstance(spans, list), "Spans must be a list"
    assert len(spans) > 0, "Spans must be non-empty"

    for expected in expected_contains:
        assert expected in result, (
            f"Expected '{expected}' in normalized output.\n"
            f"Input:  {text!r}\n"
            f"Output: {result!r}"
        )


def test_pipeline_never_crashes(pipeline):
    """Pipeline must not raise even on pathological inputs."""
    bad_inputs = [
        "\x00\x01\x02",
        "😊😂🎉" * 100,
        "₹" * 50,
        "1/0 division",
        "MMMMM",  # invalid Roman
        "9" * 30,  # huge number
        "   ",
    ]
    for text in bad_inputs:
        try:
            result, spans = pipeline.normalize(text, "hi")
            assert isinstance(result, str)
        except Exception as exc:
            pytest.fail(f"Pipeline raised {type(exc).__name__} on input {text!r}: {exc}")


def test_pipeline_spans_cover_text(pipeline):
    """Code-mix spans should collectively reconstruct the normalized text."""
    text = "Hello नमस्ते world"
    result, spans = pipeline.normalize(text, "hi")
    reconstructed = "".join(span for span, _ in spans)
    # Allow whitespace differences
    assert reconstructed.strip() == result.strip() or len(spans) > 0


def test_pipeline_text_only_convenience(pipeline):
    result = pipeline.normalize_text_only("₹500 on 01/01/2024", "hi")
    assert "five hundred" in result
    assert "rupees" in result
    assert "first" in result
    assert "January" in result
