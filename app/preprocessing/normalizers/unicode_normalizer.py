"""
app/preprocessing/normalizers/unicode_normalizer.py
=====================================================
Stage 1 — Unicode normalization and control-character stripping.

Converts all input to NFC form (canonical decomposition followed by
canonical composition) and removes invisible / non-printable control
characters that would confuse downstream normalizers or TTS engines.

Preserves:
  - All printable Unicode (Devanagari, Tamil, Telugu, Latin, etc.)
  - Normal whitespace (space, newline, tab)
  - Soft hyphen (U+00AD) — stripped as non-printable

Removes:
  - C0/C1 control codes (except \\t, \\n, \\r)
  - Unicode category Cf (format chars) except ZWNJ (U+200C) which some
    Indic scripts legitimately use for conjunct prevention.
"""

from __future__ import annotations

import unicodedata

from app.core.logger import get_logger

log = get_logger(__name__)

# Zero-width non-joiner (U+200C) — used legitimately in some Indic scripts
_ZWNJ = "\u200c"
# Soft hyphen (U+00AD) — invisible, should be stripped
_SOFT_HYPHEN = "\u00ad"


class UnicodeNormalizer:
    """
    Stage 1 normalizer: NFC + control-character stripping.

    Safe to call on any string; never raises — worst case returns the
    best-effort cleaned version and logs a warning.
    """

    def normalize(self, text: str, lang: str = "hi") -> str:
        """
        Normalize *text* to NFC and strip invisible/control characters.

        Args:
            text: Raw input string.
            lang: BCP-47 language code (not used at this stage, kept for
                  interface consistency with other normalizers).

        Returns:
            NFC-normalized, cleaned string.
        """
        if not text:
            return text

        try:
            # NFC normalization
            normalized = unicodedata.normalize("NFC", text)

            # Strip unwanted characters
            cleaned_chars: list[str] = []
            for ch in normalized:
                cat = unicodedata.category(ch)
                # Keep: printable chars, whitespace (Zs/Cc-but-whitespace)
                # Keep ZWNJ explicitly (Cf category but used in Indic)
                if ch == _ZWNJ:
                    cleaned_chars.append(ch)
                elif ch == _SOFT_HYPHEN:
                    continue  # strip soft hyphen
                elif cat.startswith("C"):
                    # Control / format / surrogate / private-use
                    # Allow only basic whitespace control chars
                    if ch in ("\t", "\n", "\r"):
                        cleaned_chars.append(ch)
                    # else: strip silently
                else:
                    cleaned_chars.append(ch)

            result = "".join(cleaned_chars)

            if result != text:
                log.debug(
                    "UnicodeNormalizer: input len=%d → output len=%d",
                    len(text),
                    len(result),
                )
            return result

        except Exception as exc:  # noqa: BLE001
            log.warning("UnicodeNormalizer failed, returning original: %s", exc)
            return text
