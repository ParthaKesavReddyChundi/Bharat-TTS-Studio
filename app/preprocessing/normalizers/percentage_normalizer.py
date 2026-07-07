"""
app/preprocessing/normalizers/percentage_normalizer.py
=======================================================
Stage 10 — Percentage verbalization.

  50%     → "fifty percent"
  3.5%    → "three point five percent"
  100%    → "one hundred percent"
  -2.5%   → "minus two point five percent"
"""

from __future__ import annotations

import re

from app.core.logger import get_logger
from app.preprocessing.normalizers.number_normalizer import indian_int_to_words

log = get_logger(__name__)

_PERCENT_RE = re.compile(
    r"(-?\d+(?:\.\d+)?)\s*%"
)

_DIGIT_WORDS = ["zero","one","two","three","four","five","six","seven","eight","nine"]


class PercentageNormalizer:
    """Stage 10: Convert percentage expressions to spoken words."""

    def normalize(self, text: str, lang: str = "hi") -> str:
        def _replace(m: re.Match) -> str:
            try:
                raw = m.group(1)
                neg = raw.startswith("-")
                raw_abs = raw.lstrip("-")
                if "." in raw_abs:
                    int_part, dec_part = raw_abs.split(".", 1)
                    int_words = indian_int_to_words(int(int_part))
                    dec_words = " ".join(_DIGIT_WORDS[int(d)] for d in dec_part)
                    num_words = f"{int_words} point {dec_words}"
                else:
                    num_words = indian_int_to_words(int(raw_abs))
                prefix = "minus " if neg else ""
                return f"{prefix}{num_words} percent"
            except Exception:  # noqa: BLE001
                return m.group(0)

        return _PERCENT_RE.sub(_replace, text)
