"""
app/preprocessing/normalizers/code_mix_segmenter.py
====================================================
Stage 14 — Code-mixed text segmentation.

Splits text with interleaved English and Indic spans, tagging each span
with its detected language. Output is both:
  1. A processed string (unchanged text — segmenter only annotates)
  2. A list of (span, lang_code) tuples consumed by InferenceEngine

Supported Indic scripts and their Unicode ranges:
  Devanagari (hi, mr, ne, sa)   U+0900–U+097F
  Bengali (bn, as)              U+0980–U+09FF
  Gujarati (gu)                 U+0A80–U+0AFF
  Gurmukhi (pa)                 U+0A00–U+0A7F
  Kannada (kn)                  U+0C80–U+0CFF
  Malayalam (ml)                U+0D00–U+0D7F
  Odia (or)                     U+0B00–U+0B7F
  Tamil (ta)                    U+0B80–U+0BFF
  Telugu (te)                   U+0C00–U+0C7F

English: ASCII letters + Latin Extended

The segmenter works character-by-character, accumulating runs of the
same script and emitting a (text_span, lang_tag) pair at each transition.
"""

from __future__ import annotations

import re
import unicodedata

from app.core.logger import get_logger

log = get_logger(__name__)

# ── Script detection ranges ───────────────────────────────────────────────────

_SCRIPT_RANGES: list[tuple[int, int, str]] = [
    # (start_codepoint, end_codepoint, script_name)
    (0x0041, 0x007A, "Latin"),        # Basic Latin A-Z a-z
    (0x00C0, 0x024F, "Latin"),        # Latin Extended
    (0x0900, 0x097F, "Devanagari"),
    (0x0980, 0x09FF, "Bengali"),
    (0x0A00, 0x0A7F, "Gurmukhi"),
    (0x0A80, 0x0AFF, "Gujarati"),
    (0x0B00, 0x0B7F, "Odia"),
    (0x0B80, 0x0BFF, "Tamil"),
    (0x0C00, 0x0C7F, "Telugu"),
    (0x0C80, 0x0CFF, "Kannada"),
    (0x0D00, 0x0D7F, "Malayalam"),
]

_SCRIPT_TO_LANG: dict[str, str] = {
    "Devanagari": "hi",
    "Bengali": "bn",
    "Gurmukhi": "pa",
    "Gujarati": "gu",
    "Odia": "or",
    "Tamil": "ta",
    "Telugu": "te",
    "Kannada": "kn",
    "Malayalam": "ml",
    "Latin": "en",
}


def _detect_script(ch: str) -> str | None:
    """Return script name for a character, or None if unknown/neutral."""
    cp = ord(ch)
    for start, end, script in _SCRIPT_RANGES:
        if start <= cp <= end:
            return script
    # Also check Unicode script property as fallback
    try:
        name = unicodedata.name(ch, "")
        for script in _SCRIPT_TO_LANG:
            if script.upper() in name.upper():
                return script
    except Exception:  # noqa: BLE001
        pass
    return None  # neutral (digits, punctuation, whitespace)


SpanList = list[tuple[str, str]]  # [(text_span, lang_code), ...]


def segment(text: str, primary_lang: str = "hi") -> SpanList:
    """
    Segment *text* into (span, lang_code) pairs.

    Neutral characters (digits, punctuation, whitespace) are attached
    to the preceding span's language, or to *primary_lang* if at the start.

    Args:
        text:         Input string.
        primary_lang: Default language tag for neutral-only text.

    Returns:
        List of (span_text, lang_code) tuples.
    """
    if not text:
        return []

    spans: SpanList = []
    current_lang: str = primary_lang
    current_buf: list[str] = []

    for ch in text:
        script = _detect_script(ch)
        if script is None:
            # Neutral — attach to current buffer
            current_buf.append(ch)
        else:
            lang = _SCRIPT_TO_LANG.get(script, primary_lang)
            if lang != current_lang and current_buf:
                # Flush current buffer if it has non-neutral content
                buffered = "".join(current_buf)
                if buffered.strip():
                    spans.append((buffered, current_lang))
                elif spans:
                    # Trailing whitespace — attach to previous span
                    prev_text, prev_lang = spans[-1]
                    spans[-1] = (prev_text + buffered, prev_lang)
                    current_buf = []
                    current_lang = lang
                    current_buf.append(ch)
                    continue
                current_buf = []
                current_lang = lang
            current_lang = lang
            current_buf.append(ch)

    if current_buf:
        buffered = "".join(current_buf)
        if buffered.strip():
            spans.append((buffered, current_lang))
        elif spans:
            prev_text, prev_lang = spans[-1]
            spans[-1] = (prev_text + buffered, prev_lang)

    return spans if spans else [(text, primary_lang)]


class CodeMixSegmenter:
    """
    Stage 14: Segment code-mixed text into (span, lang) pairs.

    Note: This normalizer does NOT modify the text string — it only
    annotates it.  The pipeline stores the span list separately and
    passes it to InferenceEngine for routing decisions.
    """

    def normalize(self, text: str, lang: str = "hi") -> str:
        """Return text unchanged (segmentation stored in pipeline state)."""
        return text

    def segment(self, text: str, lang: str = "hi") -> SpanList:
        """
        Return language-tagged spans for the input text.

        Args:
            text: Input string (after previous normalizers).
            lang: Primary/document language.

        Returns:
            List of (span_text, lang_code) pairs.
        """
        return segment(text, primary_lang=lang)
