"""
app/preprocessing/normalizers/abbreviation_expander.py
=======================================================
Stage 4 — Expand common abbreviations and honorifics.

Language-aware: each language has its own expansion table imported from
lang_rules/. English-only fallback is always available.

Covers:
  Mr. / Mrs. / Ms. / Dr. / Prof. / Rev. / Jr. / Sr.
  Ltd. / Inc. / Corp. / Co. / Pvt. / Govt.
  etc. / vs. / approx. / max. / min. / no. / vol.
  Common Indian honorifics: Shri / Smt. / Km.

Trailing period is consumed; a space is added if the next char is a letter.
"""

from __future__ import annotations

import re

from app.core.logger import get_logger

log = get_logger(__name__)

# ── English abbreviation table ────────────────────────────────────────────────
# Keys: lowercase abbreviation WITH trailing dot (if applicable)
# Values: expansion (no trailing period)

_EN_ABBREV: dict[str, str] = {
    # Honorifics
    "mr.": "mister",
    "mrs.": "missus",
    "ms.": "miss",
    "dr.": "doctor",
    "prof.": "professor",
    "rev.": "reverend",
    "jr.": "junior",
    "sr.": "senior",
    "shri": "shri",
    "smt.": "shrimati",
    "km.": "kumari",
    # Corporate
    "ltd.": "limited",
    "inc.": "incorporated",
    "corp.": "corporation",
    "co.": "company",
    "pvt.": "private",
    "govt.": "government",
    # Common
    "etc.": "et cetera",
    "vs.": "versus",
    "approx.": "approximately",
    "max.": "maximum",
    "min.": "minimum",
    "no.": "number",
    "vol.": "volume",
    "pg.": "page",
    "pp.": "pages",
    "dept.": "department",
    "mgr.": "manager",
    "dir.": "director",
    "asst.": "assistant",
    "gen.": "general",
    "col.": "colonel",
    "capt.": "captain",
    "sgt.": "sergeant",
    "st.": "saint",     # ambiguous with "street" — context required
    "ave.": "avenue",
    "blvd.": "boulevard",
    "rd.": "road",
}


def _build_pattern(table: dict[str, str]) -> re.Pattern:
    """Build a case-insensitive alternation pattern from an abbreviation table."""
    # Sort longest first to avoid prefix shadowing
    keys = sorted(table.keys(), key=len, reverse=True)
    escaped = [re.escape(k) for k in keys]
    pat = r"\b(?:" + "|".join(escaped) + r")"
    return re.compile(pat, re.IGNORECASE)


_EN_PATTERN = _build_pattern(_EN_ABBREV)


class AbbreviationExpander:
    """Stage 4: Expand abbreviations and honorifics to full spoken forms."""

    def __init__(self) -> None:
        self._tables: dict[str, dict[str, str]] = {"en": _EN_ABBREV}
        self._patterns: dict[str, re.Pattern] = {"en": _EN_PATTERN}
        self._load_lang_rules()

    def _load_lang_rules(self) -> None:
        """Load language-specific abbreviation tables from lang_rules/."""
        for lang_code in ("hi", "ta", "te"):
            try:
                module_path = f"app.preprocessing.lang_rules.{lang_code}_rules"
                import importlib  # noqa: PLC0415
                module = importlib.import_module(module_path)
                if hasattr(module, "ABBREVIATIONS"):
                    merged = {**_EN_ABBREV, **module.ABBREVIATIONS}
                    self._tables[lang_code] = merged
                    self._patterns[lang_code] = _build_pattern(merged)
                    log.debug("AbbreviationExpander: loaded %s rules", lang_code)
            except Exception as exc:  # noqa: BLE001
                log.debug("AbbreviationExpander: no extra rules for %s (%s)", lang_code, exc)

    def normalize(self, text: str, lang: str = "hi") -> str:
        """
        Expand abbreviations in *text* using language-specific tables.

        Args:
            text: Input string.
            lang: BCP-47 language code.

        Returns:
            Text with abbreviations expanded.
        """
        lang_key = lang.lower()
        pattern = self._patterns.get(lang_key, self._patterns.get("en", _EN_PATTERN))
        table = self._tables.get(lang_key, self._tables.get("en", _EN_ABBREV))

        def _replace(m: re.Match) -> str:
            matched = m.group(0)
            expansion = table.get(matched.lower(), matched)
            return expansion

        return pattern.sub(_replace, text)
