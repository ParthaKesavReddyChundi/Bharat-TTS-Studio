"""
app/models/base_adapter.py
==========================
Abstract base class for all TTS model adapters.
Defines the standard interface for loading models and generating audio.
"""

from __future__ import annotations

import abc
from typing import Any

import numpy as np

from app.core.logger import get_logger

log = get_logger(__name__)


class TTSModelAdapter(abc.ABC):
    """
    Abstract interface for TTS models.
    All inference adapters must implement this contract.
    """

    def __init__(self, model_id: str, model_config: dict[str, Any]) -> None:
        """
        Initialize the adapter.

        Args:
            model_id: The unique identifier for this model (e.g. 'mms-tts-hin').
            model_config: Configuration dictionary for this model from the catalog.
        """
        self.model_id = model_id
        self.model_config = model_config
        self.is_loaded = False
        self.device = "cpu"

    @abc.abstractmethod
    def load(self, device: str = "cpu") -> bool:
        """
        Load the model into memory/VRAM.

        Args:
            device: 'cpu' or 'cuda'.

        Returns:
            bool: True if loaded successfully, False otherwise.
        """
        pass

    @abc.abstractmethod
    def unload(self) -> None:
        """
        Unload the model to free VRAM/memory.
        """
        pass

    @abc.abstractmethod
    def generate_audio(self, text: str, lang: str = "hi", speaker_id: str | None = None) -> tuple[np.ndarray, int]:
        """
        Generate audio for the given text.

        Args:
            text: The normalized text to synthesize.
            lang: Target language code (e.g. 'hi', 'te').
            speaker_id: Optional speaker ID for multi-speaker models.

        Returns:
            Tuple containing:
            - np.ndarray: The generated audio waveform as a 1D float32 array.
            - int: The sampling rate of the audio (e.g., 16000, 22050).
        """
        pass
