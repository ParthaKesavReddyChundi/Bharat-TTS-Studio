"""
app/preprocessing/normalizers/contact_pattern_normalizer.py
============================================================
Stage 3 — Contact patterns: email, URL, phone, hashtag, @mention.

Converts:
  user@example.com    → "user at example dot com"
  https://example.com → "example dot com"
  +91-9876543210      → "plus nine one nine eight seven six five four three two one zero"
  +919876543210       → same
  9876543210          → (10-digit Indian mobile) → "nine eight seven six five four three two one zero"
  #trending           → "hashtag trending"
  @username           → "at username"
"""

from __future__ import annotations

import re

from app.core.logger import get_logger

log = get_logger(__name__)

_DIGIT_WORDS = [
    "zero", "one", "two", "three", "four",
    "five", "six", "seven", "eight", "nine",
]


def _digits_to_words(digits: str) -> str:
    """Spell out each digit: '123' → 'one two three'."""
    return " ".join(_DIGIT_WORDS[int(d)] for d in digits if d.isdigit())


def _verbalize_phone(raw: str) -> str:
    """Convert a phone number string to digit-by-digit spoken form."""
    # Keep only digits and leading +
    has_plus = raw.startswith("+")
    digits = re.sub(r"\D", "", raw)
    spoken = _digits_to_words(digits)
    return ("plus " + spoken) if has_plus else spoken


# ── Patterns (order matters: most specific first) ─────────────────────────────

# Email: user@domain.tld
_EMAIL_RE = re.compile(
    r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}",
    re.IGNORECASE,
)

# URL: http/https/ftp or bare domain with common TLDs
_URL_RE = re.compile(
    r"(?:https?://|ftp://|www\.)[\w\-]+(\.[\w\-]+)+(?:/[^\s]*)?",
    re.IGNORECASE,
)

# Phone: +91-XXXXXXXXXX / +91 XXXXXXXXXX / 10-digit starting with 6-9
_PHONE_RE = re.compile(
    r"(?:\+\d{1,3}[\s\-]?)?"           # optional country code
    r"(?:\(\d{2,4}\)[\s\-]?)?"         # optional area code in parens
    r"\b(?:\d[\s\-]?){9,14}\d\b"       # 10-15 digit body
)

# Indian mobile specifically (starts 6-9, exactly 10 digits, standalone)
_INDIAN_MOBILE_RE = re.compile(r"\b([6-9]\d{9})\b")

# Hashtag
_HASHTAG_RE = re.compile(r"#(\w+)")

# Mention
_MENTION_RE = re.compile(r"@(\w+)")


def _email_to_spoken(m: re.Match) -> str:
    email = m.group(0)
    parts = email.split("@")
    if len(parts) != 2:
        return email
    user, domain = parts
    domain_spoken = domain.replace(".", " dot ")
    user_spoken = re.sub(r"[._+\-]", " ", user)
    return f"{user_spoken} at {domain_spoken}"


def _url_to_spoken(m: re.Match) -> str:
    url = m.group(0)
    # Strip protocol and www
    stripped = re.sub(r"^(?:https?://|ftp://|www\.)", "", url, flags=re.IGNORECASE)
    # Strip path
    domain = stripped.split("/")[0]
    return domain.replace(".", " dot ")


class ContactPatternNormalizer:
    """Stage 3: Convert contact patterns to spoken-safe forms."""

    def normalize(self, text: str, lang: str = "hi") -> str:
        # Email before URL (email contains @, URL doesn't)
        text = _EMAIL_RE.sub(_email_to_spoken, text)
        text = _URL_RE.sub(_url_to_spoken, text)
        # Phone patterns — be conservative: only match plausible phone strings
        text = _PHONE_RE.sub(lambda m: _verbalize_phone(m.group(0)), text)
        text = _HASHTAG_RE.sub(lambda m: f"hashtag {m.group(1)}", text)
        text = _MENTION_RE.sub(lambda m: f"at {m.group(1)}", text)
        return text
