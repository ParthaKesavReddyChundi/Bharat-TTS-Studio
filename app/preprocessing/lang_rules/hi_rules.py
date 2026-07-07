"""
app/preprocessing/lang_rules/hi_rules.py
=========================================
Hindi-specific preprocessing rules.

Provides:
  ABBREVIATIONS : dict of Hindi-context abbreviation expansions
                  (merged with English table by AbbreviationExpander)
"""

# Hindi honorifics and common abbreviations
# Keys must be lowercase; values are spoken English expansions
ABBREVIATIONS: dict[str, str] = {
    # Honorifics commonly used in Hindi text
    "shri.": "shri",
    "smt.": "shrimati",
    "km.": "kumari",
    "pt.": "pandit",
    "swami.": "swami",
    # Government / institutional
    "ias": "I A S",
    "ips": "I P S",
    "ifs": "I F S",
    "mla": "M L A",
    "mp": "M P",
    "cm": "chief minister",
    "pm": "prime minister",
    # Common in Hindi press
    "vs.": "versus",
    "dr.": "doctor",
    "prof.": "professor",
}
