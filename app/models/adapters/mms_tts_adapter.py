"""
app/models/adapters/mms_tts_adapter.py
======================================
Concrete adapter for Meta's MMS-TTS models using the VITS architecture.
"""

from __future__ import annotations

import gc
from typing import Any

import numpy as np
import torch

# We lazily import transformers to avoid huge startup times if not used
try:
    from transformers import VitsModel, AutoTokenizer
except ImportError:
    VitsModel = None
    AutoTokenizer = None

from app.core.logger import get_logger
from app.models.base_adapter import TTSModelAdapter
from app.models.model_downloader import ModelDownloader

log = get_logger(__name__)


class MMSTTSAdapter(TTSModelAdapter):
    """
    Adapter for Meta MMS-TTS models (VITS based).
    Handles downloading, loading into VRAM, and synthesis.
    """

    def __init__(self, model_id: str, model_config: dict[str, Any]) -> None:
        super().__init__(model_id, model_config)
        self.model: VitsModel | None = None
        self.tokenizer: AutoTokenizer | None = None
        self.downloader = ModelDownloader()
        
        # The repo_id is required in the catalog
        self.repo_id = self.model_config.get("repo_id")
        if not self.repo_id:
            raise ValueError(f"MMS config for '{model_id}' must specify 'repo_id'")

    def load(self, device: str = "cpu") -> bool:
        if VitsModel is None:
            log.error("transformers library is not installed.")
            return False
            
        try:
            # 1. Download/Cache
            local_path = self.downloader.download_model(self.repo_id)
            
            # 2. Map device string to torch format
            self.device = "cuda" if device == "cuda" and torch.cuda.is_available() else "cpu"
            log.info("Loading MMS model '%s' from %s onto %s...", self.model_id, local_path, self.device)
            
            # 3. Load Tokenizer & Model
            self.tokenizer = AutoTokenizer.from_pretrained(local_path, local_files_only=True)
            self.model = VitsModel.from_pretrained(local_path, local_files_only=True)
            
            # 4. Move to device
            self.model.to(self.device)
            self.model.eval()
            
            self.is_loaded = True
            log.info("Successfully loaded MMS model '%s'.", self.model_id)
            return True
            
        except Exception as exc:  # noqa: BLE001
            log.error("Failed to load MMS model '%s': %s", self.model_id, exc, exc_info=True)
            self.is_loaded = False
            return False

    def unload(self) -> None:
        """Free up GPU memory."""
        log.info("Unloading MMS model '%s'...", self.model_id)
        if self.model is not None:
            self.model.cpu()  # Move to CPU first
            del self.model
            self.model = None
            
        if self.tokenizer is not None:
            del self.tokenizer
            self.tokenizer = None
            
        self.is_loaded = False
        
        # Force garbage collection and empty CUDA cache
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            
        log.info("Model '%s' unloaded.", self.model_id)

    def generate_audio(self, text: str, lang: str = "hi", speaker_id: str | None = None) -> tuple[np.ndarray, int]:
        """
        Generate audio using VITS. MMS models are single-speaker per checkpoint.
        """
        if not self.is_loaded or self.model is None or self.tokenizer is None:
            raise RuntimeError(f"Model '{self.model_id}' is not loaded.")

        if not text.strip():
            log.warning("Empty text passed to generator.")
            return np.array([], dtype=np.float32), 16000

        log.debug("Generating audio for text (len=%d) on %s", len(text), self.device)
        
        try:
            # Tokenize and move to device
            inputs = self.tokenizer(text, return_tensors="pt").to(self.device)
            
            if inputs["input_ids"].size(1) == 0:
                raise ValueError("The provided text contains no valid characters for this model. Ensure you are using the correct native script (e.g., Kannada script for Kannada models).")
                
            # Generate (no gradients needed)
            with torch.no_grad():
                output = self.model(**inputs)
                
            # The model outputs a single waveform tensor shape (1, channels, samples)
            waveform_tensor = output.waveform[0]
            
            # Move to CPU and convert to float32 numpy array
            waveform = waveform_tensor.cpu().numpy().squeeze().astype(np.float32)
            
            # VITS model config holds sampling rate (usually 16000 for MMS)
            sample_rate = self.model.config.sampling_rate
            
            log.debug("Audio generated successfully. Shape: %s, SR: %d", waveform.shape, sample_rate)
            return waveform, sample_rate
            
        except Exception as exc:
            log.error("Audio generation failed: %s", exc, exc_info=True)
            raise RuntimeError(f"Audio generation failed: {exc}") from exc
