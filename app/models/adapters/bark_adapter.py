"""
app/models/adapters/bark_adapter.py
=====================================
Adapter for Suno Bark TTS (small variant).
Bark is an LLM-based generative TTS supporting 13+ languages including Hindi.
Completely open — no gating, no HuggingFace token required.
Model: suno/bark-small (~650 MB)

Bark uses special voice presets. For Indian languages:
  - Hindi:   v2/hi_speaker_0 through v2/hi_speaker_8
  - English: v2/en_speaker_6

NOTE: Bark generation is slow (it's LLM-based). First run will download ~650 MB.
"""

from __future__ import annotations

import gc
from typing import Any

import numpy as np
import torch

try:
    from transformers import BarkModel, BarkProcessor
    _HAS_BARK = True
except ImportError:
    _HAS_BARK = False

from app.core.logger import get_logger
from app.models.base_adapter import TTSModelAdapter

log = get_logger(__name__)

# Default voice presets per language
BARK_VOICE_PRESETS: dict[str, str] = {
    "hi": "v2/hi_speaker_3",
    "en": "v2/en_speaker_6",
    "ta": "v2/hi_speaker_3",   # fallback — Bark doesn't have dedicated Tamil
    "te": "v2/hi_speaker_3",   # fallback
    "bn": "v2/hi_speaker_3",   # fallback
}


class BarkAdapter(TTSModelAdapter):
    """
    Adapter for Suno Bark (small) generative TTS.
    Multilingual LLM-based TTS with natural prosody and expression.
    All repositories are fully open with no access restrictions.
    """

    def __init__(self, model_id: str, model_config: dict[str, Any]) -> None:
        super().__init__(model_id, model_config)
        self.model: BarkModel | None = None
        self.processor: BarkProcessor | None = None
        self.repo_id = self.model_config.get("repo_id", "suno/bark-small")

    def load(self, device: str = "cpu") -> bool:
        if not _HAS_BARK:
            raise ImportError(
                "The 'transformers' package is not installed or is too old. "
                "BarkModel requires transformers >= 4.31.0"
            )

        try:
            self.device = "cuda" if device == "cuda" and torch.cuda.is_available() else "cpu"
            log.info("Loading Bark model '%s' from %s onto %s...", self.model_id, self.repo_id, self.device)

            if self.device == "cuda":
                from app.core import system_monitor  # noqa: PLC0415
                from app.core.exceptions import OutOfMemoryError  # noqa: PLC0415
                available_vram = system_monitor.get_available_vram_gb()
                if 0.0 < available_vram < 3.5:
                    raise OutOfMemoryError(self.model_id, required_gb=3.5, available_gb=available_vram)

            # Load processor and model with float16 as strictly requested
            try:
                self.processor = BarkProcessor.from_pretrained(
                    self.repo_id, 
                    torch_dtype=torch.float16
                )
                
                self.model = BarkModel.from_pretrained(
                    self.repo_id,
                    torch_dtype=torch.float16,
                ).to(self.device)
            except Exception as e:
                log.error("Native model load failure", exc_info=True)
                from app.core.exceptions import ModelLoadError  # noqa: PLC0415
                raise ModelLoadError(self.model_id, f"Load failed: {str(e)}") from e

            self.model.eval()

            self.is_loaded = True
            log.info("Successfully loaded Bark model '%s'.", self.model_id)
            return True

        except Exception as exc:
            if type(exc).__name__ in ("OutOfMemoryError", "ModelLoadError"):
                raise
            log.error("Failed to load Bark model '%s': %s", self.model_id, exc, exc_info=True)
            self.is_loaded = False
            return False

    def unload(self) -> None:
        log.info("Unloading Bark model '%s'...", self.model_id)
        for attr in ("model", "processor"):
            obj = getattr(self, attr, None)
            if obj is not None:
                if hasattr(obj, "cpu"):
                    try:
                        obj.cpu()
                    except Exception:
                        pass
                del obj
                setattr(self, attr, None)

        self.is_loaded = False
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        log.info("Bark model '%s' unloaded.", self.model_id)

    def generate_audio(self, text: str, lang: str = "hi", speaker_id: str | None = None) -> tuple[np.ndarray, int]:
        if not self.is_loaded or self.model is None or self.processor is None:
            raise RuntimeError(f"Model '{self.model_id}' is not loaded.")

        if not text.strip():
            return np.array([], dtype=np.float32), 24000

        # Pick voice preset
        voice_preset = speaker_id or BARK_VOICE_PRESETS.get(lang, "v2/hi_speaker_3")
        log.info("Bark generating for lang='%s' with voice_preset='%s'", lang, voice_preset)

        try:
            inputs = self.processor(text, voice_preset=voice_preset, return_tensors="pt")
            inputs = {k: v.to(self.device) for k, v in inputs.items()}

            with torch.no_grad():
                # Generate audio array
                audio_array = self.model.generate(**inputs)

            # audio_array shape: (1, samples)
            audio = audio_array.cpu().numpy().squeeze().astype(np.float32)

            # Normalize to [-1, 1] if needed
            max_val = np.abs(audio).max()
            if max_val > 1.0:
                audio = audio / max_val

            sample_rate = self.model.generation_config.sample_rate
            log.debug("Bark generated %d samples at %dHz.", len(audio), sample_rate)
            return audio, sample_rate

        except Exception as exc:
            from app.core.exceptions import InferenceError  # noqa: PLC0415
            log.error("Bark audio generation failed: %s", exc, exc_info=True)
            raise InferenceError(self.model_id, f"Audio generation failed: {exc}") from exc
