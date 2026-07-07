"""
app/preprocessing/normalizers/punctuation_cleaner.py
=====================================================
Stage 15 — Final punctuation cleanup.

  - Collapse repeated punctuation: "!!!" → "!"
  - Normalize quote characters: " " → "  (straight double quotes)
  - Normalize dash variants: em-dash (—), en-dash (–) → " - "
  - Remove stray pipe, caret, backtick, tilde, backslash
  - Collapse multiple spaces/newlines to single space
  - Strip leading/trailing whitespace

This is the LAST stage; it cleans up any noise introduced by
earlier normalizers.
"""

from __future__ import annotations

import re

from app.core.logger import get_logger

log = get_logger(__name__)


class PunctuationCleaner:
    """Stage 15: Final punctuation normalization and whitespace collapse."""

    # Repeated punctuation (keep one): !! → !  ?? → ?  .. → .  (but ... ellipsis handled)
    _REPEAT_PUNCT = re.compile(r"([!?,;:])\1+")

    # Ellipsis variants: ... or …
    _ELLIPSIS = re.compile(r"\.{2,}|…")

    # Typographic quote normalization
    _OPEN_QUOTE = re.compile(r"[\u201C\u201F\u00AB\u2018\u201B]")   # " « '
    _CLOSE_QUOTE = re.compile(r"[\u201D\u201E\u00BB\u2019\u201A]")  # " » '

    # Dash normalization
    _EM_DASH = re.compile(r"\s*[\u2014\u2015]\s*")    # — (em dash)
    _EN_DASH = re.compile(r"\s*[\u2013]\s*")           # – (en dash)

    # Stray characters that carry no spoken meaning
    _STRAY = re.compile(r"[|^`~\\]")

    # Collapse multiple whitespace (including newlines) to single space
    _MULTI_SPACE = re.compile(r"\s+")

    def normalize(self, text: str, lang: str = "hi") -> str:
        """
        Apply all punctuation cleanup rules to *text*.

        Args:
            text: Input string (last stage — receives fully normalized text).
            lang: BCP-47 code (unused; kept for interface consistency).

        Returns:
            Cleaned string.
        """
        # 1. Ellipsis → pause marker (comma + space)
        text = self._ELLIPSIS.sub(", ", text)

        # 2. Repeated punctuation collapse
        text = self._REPEAT_PUNCT.sub(r"\1", text)

        # 3. Quote normalization
        text = self._OPEN_QUOTE.sub('"', text)
        text = self._CLOSE_QUOTE.sub('"', text)

        # 4. Dash normalization
        text = self._EM_DASH.sub(" - ", text)
        text = self._EN_DASH.sub(" - ", text)

        # 5. Remove stray characters
        text = self._STRAY.sub(" ", text)

        # 6. Collapse multiple whitespace
        text = self._MULTI_SPACE.sub(" ", text)

        # 7. Strip edges
        text = text.strip()

        return text
