"""
app/utils/i18n_labels.py
========================
Language and script mapping utility.
"""

_LANG_MAP = {
    "hi": "Hindi",
    "ta": "Tamil",
    "te": "Telugu",
    "mr": "Marathi",
    "gu": "Gujarati",
    "bn": "Bengali",
    "kn": "Kannada",
    "ml": "Malayalam",
    "pa": "Punjabi",
    "ur": "Urdu",
    "en": "English",
    "or": "Odia",
    "as": "Assamese",
    "sa": "Sanskrit",
    "ne": "Nepali",
    "sd": "Sindhi"
}

def get_language_name(lang_code: str) -> str:
    """
    Get the English display name for a BCP-47 / ISO 639-1 language code.
    If the code is unknown, returns the code itself in uppercase.
    """
    return _LANG_MAP.get(lang_code.lower(), lang_code.upper())
