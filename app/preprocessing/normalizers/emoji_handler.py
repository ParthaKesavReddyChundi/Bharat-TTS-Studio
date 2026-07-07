"""
app/preprocessing/normalizers/emoji_handler.py
===============================================
Stage 2 — Emoji stripping or verbalization.

Modes (configured via settings):
  - "strip"     : remove all emoji characters silently
  - "verbalize" : replace emoji with a textual description in brackets,
                  e.g. 😊 → "[smiling face]"

Falls back to "strip" for unknown emoji (no description available).
"""

from __future__ import annotations

import re
import unicodedata

from app.core.logger import get_logger

log = get_logger(__name__)

# Regex matching emoji and pictographic symbols
# Covers: Emoticons, Misc Symbols, Dingbats, Transport/Map, Supplemental
_EMOJI_RE = re.compile(
    "["
    "\U0001F600-\U0001F64F"  # emoticons
    "\U0001F300-\U0001F5FF"  # misc symbols and pictographs
    "\U0001F680-\U0001F6FF"  # transport & map
    "\U0001F700-\U0001F77F"  # alchemical symbols
    "\U0001F780-\U0001F7FF"  # geometric shapes extended
    "\U0001F800-\U0001F8FF"  # supplemental arrows-C
    "\U0001F900-\U0001F9FF"  # supplemental symbols and pictographs
    "\U0001FA00-\U0001FA6F"  # chess symbols
    "\U0001FA70-\U0001FAFF"  # symbols and pictographs extended-A
    "\U00002702-\U000027B0"  # dingbats
    "\U000024C2-\U0001F251"  # enclosed chars
    "]+",
    flags=re.UNICODE,
)


def _describe_emoji(emoji_str: str) -> str:
    """Return a bracketed description for the first emoji in the string."""
    try:
        name = unicodedata.name(emoji_str[0], "").lower()
        if name:
            return f"[{name}]"
    except Exception:  # noqa: BLE001
        pass
    return ""


class EmojiHandler:
    """Stage 2: Strip or verbalize emoji characters."""

    def __init__(self, mode: str = "strip") -> None:
        self._mode = mode.lower()

    def normalize(self, text: str, lang: str = "hi") -> str:
        """
        Process emoji in *text* according to the configured mode.

        Args:
            text: Input string.
            lang: BCP-47 code (unused, kept for interface consistency).

        Returns:
            Processed string with emoji handled.
        """
        if self._mode == "verbalize":
            return _EMOJI_RE.sub(lambda m: _describe_emoji(m.group(0)) or "", text)
        else:
            # strip mode (default)
            return _EMOJI_RE.sub("", text)
