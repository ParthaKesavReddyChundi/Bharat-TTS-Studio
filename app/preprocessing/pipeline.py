"""
app/preprocessing/pipeline.py
==============================
Preprocessing pipeline orchestrator.

Runs all 15 normalizers in the order defined in §9 of the spec.
Each normalizer is a pure function (stateless for the given call);
the pipeline is the only stateful object.

Output: (normalized_text, span_list)
  - normalized_text: string ready to feed to TTS adapter
  - span_list: list of (span, lang_code) from CodeMixSegmenter,
               used by InferenceEngine for routing code-mixed text

Usage:
    from app.preprocessing.pipeline import PreprocessingPipeline
    pipeline = PreprocessingPipeline(emoji_mode="strip")
    text, spans = pipeline.normalize("Hello! ₹2500 on 23/05/2026", lang="hi")
"""

from __future__ import annotations

from app.core.logger import get_logger
from app.preprocessing.normalizers.unicode_normalizer import UnicodeNormalizer
from app.preprocessing.normalizers.emoji_handler import EmojiHandler
from app.preprocessing.normalizers.contact_pattern_normalizer import ContactPatternNormalizer
from app.preprocessing.normalizers.abbreviation_expander import AbbreviationExpander
from app.preprocessing.normalizers.date_time_normalizer import DateTimeNormalizer
from app.preprocessing.normalizers.currency_normalizer import CurrencyNormalizer
from app.preprocessing.normalizers.number_normalizer import NumberNormalizer
from app.preprocessing.normalizers.ordinal_normalizer import OrdinalNormalizer
from app.preprocessing.normalizers.fraction_scientific_normalizer import FractionScientificNormalizer
from app.preprocessing.normalizers.percentage_normalizer import PercentageNormalizer
from app.preprocessing.normalizers.unit_measurement_normalizer import UnitMeasurementNormalizer
from app.preprocessing.normalizers.roman_numeral_normalizer import RomanNumeralNormalizer
from app.preprocessing.normalizers.pincode_vehicle_normalizer import PincodeVehicleNormalizer
from app.preprocessing.normalizers.code_mix_segmenter import CodeMixSegmenter, SpanList
from app.preprocessing.normalizers.punctuation_cleaner import PunctuationCleaner

log = get_logger(__name__)

# ── Pipeline stage order (must match §9 of spec exactly) ─────────────────────
#
#  1  UnicodeNormalizer
#  2  EmojiHandler
#  3  ContactPatternNormalizer
#  4  AbbreviationExpander
#  5  DateTimeNormalizer
#  6  CurrencyNormalizer
#  7  NumberNormalizer
#  8  OrdinalNormalizer
#  9  FractionScientificNormalizer
# 10  PercentageNormalizer
# 11  UnitMeasurementNormalizer
# 12  RomanNumeralNormalizer
# 13  PincodeVehicleNormalizer
# 14  CodeMixSegmenter          (annotates; does NOT modify text)
# 15  PunctuationCleaner


class PreprocessingPipeline:
    """
    Ordered, deterministic text normalization pipeline.

    Each stage is independently unit-testable as a pure function.
    The pipeline itself is thread-safe for reads (stateless per call)
    after construction.
    """

    def __init__(self, emoji_mode: str = "strip") -> None:
        self._unicode = UnicodeNormalizer()
        self._emoji = EmojiHandler(mode=emoji_mode)
        self._contact = ContactPatternNormalizer()
        self._abbrev = AbbreviationExpander()
        self._datetime = DateTimeNormalizer()
        self._currency = CurrencyNormalizer()
        self._number = NumberNormalizer()
        self._ordinal = OrdinalNormalizer()
        self._fraction = FractionScientificNormalizer()
        self._percent = PercentageNormalizer()
        self._unit = UnitMeasurementNormalizer()
        self._roman = RomanNumeralNormalizer()
        self._pincode = PincodeVehicleNormalizer()
        self._codemix = CodeMixSegmenter()
        self._punct = PunctuationCleaner()

        log.info("PreprocessingPipeline initialised (emoji_mode=%s).", emoji_mode)

    def normalize(self, text: str, lang: str = "hi") -> tuple[str, SpanList]:
        """
        Run the full 15-stage pipeline on *text*.

        Args:
            text: Raw input text from the user.
            lang: BCP-47 primary language code (e.g. "hi", "ta", "te").

        Returns:
            Tuple of:
              - normalized_text: clean, TTS-ready string
              - spans: list of (span_text, lang_code) for code-mix routing

        Raises:
            Never raises — any normalizer failure is caught and logged;
            the best-effort result is returned.
        """
        if not text or not text.strip():
            return text, [(text, lang)]

        original_len = len(text)
        log.debug("Pipeline start: lang=%s, len=%d", lang, original_len)

        try:
            # Stage 1
            text = self._unicode.normalize(text, lang)
            # Stage 2
            text = self._emoji.normalize(text, lang)
            # Stage 3
            text = self._contact.normalize(text, lang)
            # Stage 4
            text = self._abbrev.normalize(text, lang)
            # Stage 5
            text = self._datetime.normalize(text, lang)
            # Stage 6
            text = self._currency.normalize(text, lang)
            # Stage 8
            text = self._ordinal.normalize(text, lang)
            # Stage 9
            text = self._fraction.normalize(text, lang)
            # Stage 10
            text = self._percent.normalize(text, lang)
            # Stage 11
            text = self._unit.normalize(text, lang)
            # Stage 12
            text = self._roman.normalize(text, lang)
            # Stage 13
            text = self._pincode.normalize(text, lang)
            # Stage 7 - Generic NumberNormalizer runs after all specific patterns
            text = self._number.normalize(text, lang)
            # Stage 14 — annotate spans (does not change text)
            spans = self._codemix.segment(text, lang)
            # Stage 15
            text = self._punct.normalize(text, lang)

            log.debug(
                "Pipeline done: len %d → %d, %d spans",
                original_len, len(text), len(spans),
            )
            return text, spans

        except Exception as exc:  # noqa: BLE001
            log.error("PreprocessingPipeline failed: %s", exc, exc_info=True)
            # Best-effort: return whatever we have
            return text, [(text, lang)]

    def normalize_text_only(self, text: str, lang: str = "hi") -> str:
        """
        Convenience wrapper that returns only the normalized string
        (discards span list). Useful for quick testing.
        """
        result, _ = self.normalize(text, lang)
        return result
