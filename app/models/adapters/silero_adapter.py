"""
app/models/adapters/silero_adapter.py
========================================
Adapter for Silero TTS models loaded via PyTorch Hub.
Silero is a family of compact, high-quality VITS models.
Completely open — no gating, no HuggingFace token required.
Supports Hindi (v3_indic) and other Indic/global languages.

Silero Hub URL: https://github.com/snakers4/silero-models
"""

from __future__ import annotations

import gc
import os
from typing import Any

import numpy as np
import torch

from app.core.logger import get_logger
from app.models.base_adapter import TTSModelAdapter

log = get_logger(__name__)

# Silero model specs — maps language code to (model_id, speaker, sample_rate)
SILERO_LANG_SPECS: dict[str, tuple[str, str, int]] = {
    "hi": ("v3_indic", "hindi_male", 48000),
    "mr": ("v3_indic", "hindi_male", 48000),  # closest available
    "en": ("v3_en", "en_0", 48000),
}

SILERO_REPO = "snakers4/silero-models"
SILERO_MODEL_NAME = "silero_tts"


class SileroAdapter(TTSModelAdapter):
    """
    Adapter for Silero TTS models loaded via PyTorch Hub.
    Compact (~60 MB), fast, no token required.
    """

    def __init__(self, model_id: str, model_config: dict[str, Any]) -> None:
        super().__init__(model_id, model_config)
        self.model = None
        # Config-driven language selection
        self.lang_code = self.model_config.get("language_code", "hi")
        # In PyTorch Hub for Silero, 'language' means the model group (e.g., 'indic')
        self.hub_language = self.model_config.get("hub_language", "indic")
        self.silero_model_id = self.model_config.get("silero_model_id", "v3_indic")
        self.speaker = self.model_config.get("silero_speaker", "hindi_male")
        self.sample_rate = self.model_config.get("sample_rate", 48000)

    def load(self, device: str = "cpu") -> bool:
        try:
            self.device = "cuda" if device == "cuda" and torch.cuda.is_available() else "cpu"
            log.info(
                "Loading Silero model '%s' (model_id=%s, speaker=%s) onto %s...",
                self.model_id, self.silero_model_id, self.speaker, self.device
            )

            print(f"DEBUG SILERO ARGS: repo={SILERO_REPO} model={SILERO_MODEL_NAME} lang={self.hub_language} speaker={self.silero_model_id}")
            self.model, example_text = torch.hub.load(
                repo_or_dir=SILERO_REPO,
                model=SILERO_MODEL_NAME,
                language=self.hub_language,
                speaker=self.silero_model_id,
                trust_repo=True,
            )
            print(f"DEBUG SILERO RET: {type(self.model)}, {type(example_text)}")

            self.model.to(self.device)

            self.is_loaded = True
            log.info("Successfully loaded Silero model '%s'.", self.model_id)
            return True

        except Exception as exc:
            log.error("Failed to load Silero model '%s': %s", self.model_id, exc, exc_info=True)
            self.is_loaded = False
            return False

    def unload(self) -> None:
        log.info("Unloading Silero model '%s'...", self.model_id)
        if self.model is not None:
            try:
                self.model.cpu()
            except Exception:
                pass
            del self.model
            self.model = None
        self.is_loaded = False
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        log.info("Silero model '%s' unloaded.", self.model_id)

    def generate_audio(self, text: str, lang: str = "hi", speaker_id: str | None = None) -> tuple[np.ndarray, int]:
        if not self.is_loaded or self.model is None:
            raise RuntimeError(f"Model '{self.model_id}' is not loaded.")

        if not text.strip():
            return np.array([], dtype=np.float32), self.sample_rate

        speaker = speaker_id or self.speaker

        try:
            from indic_transliteration import sanscript
            
            # Auto-transliterate Devanagari to ITRANS for Silero v3_indic if not already romanized
            # For simplicity, if text contains characters outside ASCII, transliterate.
            # (In a full app, this would use the proper script-to-script mapping)
            has_indic_chars = any(ord(c) > 127 for c in text)
            if has_indic_chars:
                log.info("Silero Adapter: Transliterating input text to ITRANS (Romanized)")
                text = sanscript.transliterate(text, sanscript.DEVANAGARI, sanscript.ITRANS)
                log.debug("Transliterated text: %s", text)

            # We must use torch.no_grad() for inference
            with torch.no_grad():
                audio_tensor = self.model.apply_tts(
                    text=text,
                    speaker=speaker,
                    sample_rate=self.sample_rate
                )

            # Silero returns a 1D CPU tensor
            audio = audio_tensor.numpy().astype(np.float32)
            log.debug("Silero generated %d samples at %dHz.", len(audio), self.sample_rate)
            return audio, self.sample_rate

        except Exception as exc:
            log.error("Silero audio generation failed: %s", exc, exc_info=True)
            raise RuntimeError(f"Audio generation failed: {exc}") from exc
