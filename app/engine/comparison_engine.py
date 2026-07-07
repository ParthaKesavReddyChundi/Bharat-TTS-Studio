"""
app/engine/comparison_engine.py
===============================
Engine for fanning out a synthesis request to multiple models concurrently.
"""

from __future__ import annotations

import time
import concurrent.futures
from dataclasses import dataclass
from typing import Any
import numpy as np

from app.core.logger import get_logger
from app.preprocessing.pipeline import PreprocessingPipeline
from app.models.model_manager import ModelManager

log = get_logger(__name__)

@dataclass
class ComparisonResult:
    model_id: str
    waveform: np.ndarray | None
    sample_rate: int
    latency_sec: float
    rtf: float
    error_msg: str | None

class ComparisonEngine:
    def __init__(self, model_manager: ModelManager | None = None) -> None:
        self.pipeline = PreprocessingPipeline()
        self.model_manager = model_manager or ModelManager()

    def run_comparison(
        self, 
        text: str, 
        primary_lang: str, 
        model_ids: list[str], 
        device: str = "cpu"
    ) -> list[ComparisonResult]:
        """
        Run inference on multiple models sequentially (to respect VRAM budgets).
        
        Note: While the UI remains responsive, we execute models one by one here 
        because 8GB VRAM cannot hold 3 TTS models at once. ModelManager's LRU
        will automatically swap them in and out.
        """
        log.info("Starting comparison across %d models: %s", len(model_ids), model_ids)
        
        # 1. Preprocess text once
        normalized_text, spans = self.pipeline.normalize(text, lang=primary_lang)
        if not normalized_text:
            log.warning("Normalized text is empty.")
            return [
                ComparisonResult(m, None, 16000, 0, 0, "Input text was empty after normalization.") 
                for m in model_ids
            ]

        results = []
        for model_id in model_ids:
            try:
                t0 = time.time()
                waveform, sr = self.model_manager.generate_audio(
                    model_id=model_id,
                    text=normalized_text,
                    lang=primary_lang,
                    device=device
                )
                latency = time.time() - t0
                
                # Calculate Real-Time Factor (RTF)
                audio_duration = len(waveform) / sr if sr > 0 else 0
                rtf = latency / audio_duration if audio_duration > 0 else 0
                
                results.append(ComparisonResult(
                    model_id=model_id,
                    waveform=waveform,
                    sample_rate=sr,
                    latency_sec=latency,
                    rtf=rtf,
                    error_msg=None
                ))
            except Exception as e:
                log.error("Comparison failed for %s: %s", model_id, e)
                results.append(ComparisonResult(
                    model_id=model_id,
                    waveform=None,
                    sample_rate=16000,
                    latency_sec=0,
                    rtf=0,
                    error_msg=str(e)
                ))

        return results
