"""
app/models/adapters/gtts_adapter.py
=====================================
Adapter for Google Translate Text-to-Speech (gTTS).
"""

from __future__ import annotations

import io
from typing import Any
import numpy as np
import librosa

try:
    from gtts import gTTS
    _HAS_GTTS = True
except ImportError:
    _HAS_GTTS = False

from app.core.logger import get_logger
from app.models.base_adapter import TTSModelAdapter

log = get_logger(__name__)

# Map of UI language codes to gTTS language codes if they differ
# Most match exactly, but just in case:
GTTS_LANG_MAP = {
    "hi": "hi",
    "ta": "ta",
    "te": "te",
    "mr": "mr",
    "bn": "bn",
    "ur": "ur",
    "gu": "gu",
    "kn": "kn",
    "ml": "ml",
    "pa": "pa",
    "ne": "ne",
}

class GTTSAdapter(TTSModelAdapter):
    """
    Adapter for Google Translate TTS API.
    Completely free and requires no API keys.
    """

    def __init__(self, model_id: str, model_config: dict[str, Any]) -> None:
        super().__init__(model_id, model_config)
        self.sample_rate = self.model_config.get("sample_rate", 24000)

    def load(self, device: str = "cpu") -> bool:
        if not _HAS_GTTS:
            log.error("gTTS is not installed. Run: pip install gTTS")
            return False

        log.info("gTTS is cloud-based. Initialized successfully.")
        self.device = device
        self.is_loaded = True
        return True

    def unload(self) -> None:
        log.info("Unloading gTTS model '%s'...", self.model_id)
        self.is_loaded = False

    def generate_audio(self, text: str, lang: str = "hi", speaker_id: str | None = None) -> tuple[np.ndarray, int]:
        if not self.is_loaded:
            raise RuntimeError(f"Model '{self.model_id}' is not loaded.")

        if not text.strip():
            return np.array([], dtype=np.float32), self.sample_rate

        gtts_lang = GTTS_LANG_MAP.get(lang, lang)
        
        log.info("Generating audio with gTTS (lang=%s)...", gtts_lang)

        try:
            tts = gTTS(text=text, lang=gtts_lang)
            fp = io.BytesIO()
            tts.write_to_fp(fp)
            fp.seek(0)
            
            # gTTS returns MP3 format. Librosa can decode it.
            audio, sr = librosa.load(fp, sr=self.sample_rate)
            audio = audio.astype(np.float32)
            
            log.debug("gTTS generated %d samples at %dHz.", len(audio), sr)
            return audio, sr

        except Exception as exc:
            log.error("gTTS audio generation failed: %s", exc, exc_info=True)
            raise RuntimeError(f"Audio generation failed: {exc}") from exc
