"""
app/core/audio_manager.py
=========================
Handles playing and saving audio using sounddevice and soundfile.
"""

import numpy as np
import sounddevice as sd
import soundfile as sf

from app.core.logger import get_logger

log = get_logger(__name__)


class AudioManager:
    """
    Manages audio playback and saving.
    """

    @staticmethod
    def play(waveform: np.ndarray, sample_rate: int, blocking: bool = False) -> None:
        """
        Play the given waveform.

        Args:
            waveform: 1D or 2D numpy array containing audio data.
            sample_rate: The sampling rate of the audio.
            blocking: If True, blocks execution until playback finishes.
        """
        try:
            log.debug("Playing audio... (SR: %d, Length: %d samples)", sample_rate, len(waveform))
            # sounddevice plays asynchronously by default, blocking=True uses sd.wait()
            sd.play(waveform, samplerate=sample_rate)
            if blocking:
                sd.wait()
        except Exception as exc:
            log.error("Failed to play audio: %s", exc)

    @staticmethod
    def stop() -> None:
        """Stop any currently playing audio."""
        try:
            sd.stop()
            log.debug("Audio playback stopped.")
        except Exception as exc:
            log.error("Failed to stop audio: %s", exc)

    @staticmethod
    def save(filepath: str, waveform: np.ndarray, sample_rate: int) -> bool:
        """
        Save the waveform to a WAV file.

        Args:
            filepath: Path to save the audio file.
            waveform: The audio data.
            sample_rate: The sampling rate.

        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            sf.write(filepath, waveform, sample_rate)
            log.info("Saved audio to %s", filepath)
            return True
        except Exception as exc:
            log.error("Failed to save audio to %s: %s", filepath, exc)
            return False
