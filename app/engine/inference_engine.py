"""
app/engine/inference_engine.py
==============================
High-level engine that combines text preprocessing and model inference.
"""

from __future__ import annotations

import numpy as np

from app.core.logger import get_logger
from app.preprocessing.pipeline import PreprocessingPipeline
from app.models.model_manager import ModelManager

log = get_logger(__name__)


class InferenceEngine:
    """
    Orchestrates the entire TTS process from raw text to final audio.
    """

    def __init__(self, model_manager: ModelManager | None = None) -> None:
        self.pipeline = PreprocessingPipeline()
        self.model_manager = model_manager or ModelManager()

    def synthesize(self, text: str, primary_model_id: str, speaker_id: str | None = None, device: str = "cpu") -> tuple[np.ndarray, int]:
        """
        Convert raw text into synthesized audio.

        Args:
            text: The raw input text.
            primary_model_id: The ID of the model to use (e.g. 'mms-tts-hin').
            speaker_id: The specific speaker ID to use (if supported).
            device: 'cpu' or 'cuda'.

        Returns:
            Tuple of (waveform: np.ndarray, sample_rate: int)
        """
        log.info("Starting synthesis for model '%s'", primary_model_id)
        
        # 1. Preprocess text
        # For this version, we will process the entire text as a single string 
        # using the primary language, or we can iterate over spans.
        # MMS models don't handle code-mixing well, so we rely on the transliterator
        # step in the pipeline (which we will implement fully in later phases).
        
        # Assuming the pipeline normalizes English numerals into target language
        primary_lang = self.model_manager.models_config.get(primary_model_id, {}).get("languages", ["hi"])[0]
        normalized_text, spans = self.pipeline.normalize(text, lang=primary_lang)
        
        # 2. Log normalized text
        log.debug("Normalized text: %s", normalized_text)
        
        # 3. Generate Audio
        if not normalized_text:
            log.warning("Normalized text is empty. Returning empty audio.")
            return np.array([], dtype=np.float32), 16000
            
        waveform, sr = self.model_manager.generate_audio(
            model_id=primary_model_id,
            text=normalized_text,
            lang=primary_lang,
            speaker_id=speaker_id,
            device=device
        )
        
        log.info("Synthesis complete. Output length: %d samples", len(waveform))
        return waveform, sr
