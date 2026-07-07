"""
app/models/adapters/edge_tts_adapter.py
=========================================
Adapter for Microsoft Edge TTS.
"""

from __future__ import annotations

import asyncio
import io
import gc
from typing import Any

import numpy as np
import librosa

try:
    import edge_tts
    _HAS_EDGE_TTS = True
except ImportError:
    _HAS_EDGE_TTS = False

from app.core.logger import get_logger
from app.models.base_adapter import TTSModelAdapter

log = get_logger(__name__)


class EdgeTTSAdapter(TTSModelAdapter):
    """
    Adapter for Microsoft Edge TTS Cloud API.
    """

    def __init__(self, model_id: str, model_config: dict[str, Any]) -> None:
        super().__init__(model_id, model_config)
        self.sample_rate = self.model_config.get("sample_rate", 24000)

    def load(self, device: str = "cpu") -> bool:
        if not _HAS_EDGE_TTS:
            log.error("edge_tts is not installed. Run: pip install edge-tts")
            return False

        # Edge TTS requires no actual loading into memory/GPU
        log.info("Edge TTS is cloud-based. Initialized successfully.")
        self.device = device
        self.is_loaded = True
        return True

    def unload(self) -> None:
        log.info("Unloading Edge TTS model '%s'...", self.model_id)
        self.is_loaded = False
        gc.collect()

    def generate_audio(self, text: str, lang: str = "hi", speaker_id: str | None = None) -> tuple[np.ndarray, int]:
        if not self.is_loaded:
            raise RuntimeError(f"Model '{self.model_id}' is not loaded.")

        if not text.strip():
            return np.array([], dtype=np.float32), self.sample_rate

        # Default fallback if speaker_id is not provided
        voice = speaker_id if speaker_id else "hi-IN-MadhurNeural"
        
        log.info("Generating audio with Edge TTS (voice=%s)...", voice)

        try:
            # We need an event loop to run edge_tts
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
            audio_data = loop.run_until_complete(self._fetch_edge_audio(text, voice))
            
            # Decode MP3 using librosa
            log.debug("Decoding %d bytes of MP3 data...", len(audio_data))
            audio, sr = librosa.load(io.BytesIO(audio_data), sr=self.sample_rate)
            
            audio = audio.astype(np.float32)
            log.debug("Edge TTS generated %d samples at %dHz.", len(audio), sr)
            return audio, sr

        except Exception as exc:
            log.error("Edge TTS audio generation failed: %s", exc, exc_info=True)
            raise RuntimeError(f"Audio generation failed: {exc}") from exc

    async def _fetch_edge_audio(self, text: str, voice: str) -> bytes:
        communicate = edge_tts.Communicate(text, voice)
        audio_data = b""
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data += chunk["data"]
        return audio_data
