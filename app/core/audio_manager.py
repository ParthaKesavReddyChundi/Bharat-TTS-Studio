"""
app/core/audio_manager.py
=========================
Handles playing and saving audio using sounddevice and soundfile.
Supports WAV (always) and MP3 (requires pydub + ffmpeg).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import sounddevice as sd
import soundfile as sf

from app.core.logger import get_logger

log = get_logger(__name__)

# Optional pydub for MP3 encoding
try:
    from pydub import AudioSegment
    _HAS_PYDUB = True
except ImportError:
    _HAS_PYDUB = False
    log.info("pydub not installed — MP3 export unavailable (WAV will be used as fallback).")


class AudioManager:
    """
    Manages audio playback and saving.

    Supported output formats
    ------------------------
    - **.wav** — Always available via soundfile (lossless, recommended).
    - **.mp3** — Available when ``pydub`` and an ffmpeg binary are present.
      Falls back to WAV and renames the extension accordingly.
    """

    # ── Playback ──────────────────────────────────────────────────────────────

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

    # ── Saving ────────────────────────────────────────────────────────────────

    @staticmethod
    def save(filepath: str, waveform: np.ndarray, sample_rate: int) -> bool:
        """
        Save the waveform to a file.  Format is inferred from the extension.

        Supported extensions: ``.wav``, ``.mp3``.
        If MP3 is requested but ``pydub`` is unavailable, the file is saved
        as WAV and the path's extension is silently corrected.

        Args:
            filepath: Destination path, e.g. ``/out/speech.wav`` or ``/out/speech.mp3``.
            waveform: The audio data (1D float32 numpy array normalised to ±1).
            sample_rate: The sampling rate in Hz.

        Returns:
            bool: True if the file was written successfully, False otherwise.
        """
        path = Path(filepath)
        ext = path.suffix.lower()

        if ext == ".mp3":
            return AudioManager._save_mp3(path, waveform, sample_rate)

        # Default / fallback — WAV via soundfile
        return AudioManager._save_wav(path, waveform, sample_rate)

    # ── Internal helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _save_wav(path: Path, waveform: np.ndarray, sample_rate: int) -> bool:
        """Write a WAV file using soundfile."""
        try:
            sf.write(str(path), waveform, sample_rate)
            log.info("Saved WAV audio to %s", path)
            return True
        except Exception as exc:
            log.error("Failed to save WAV audio to %s: %s", path, exc)
            return False

    @staticmethod
    def _save_mp3(path: Path, waveform: np.ndarray, sample_rate: int) -> bool:
        """
        Encode as MP3 using pydub.

        If pydub is unavailable, falls back to WAV (same directory, ``.wav`` extension).
        The float32 array is converted to int16 PCM before encoding — pydub
        requires integer PCM input.
        """
        if not _HAS_PYDUB:
            log.warning(
                "pydub is not installed — saving as WAV instead of MP3. "
                "Install with: pip install pydub  (also requires ffmpeg on PATH)."
            )
            wav_path = path.with_suffix(".wav")
            return AudioManager._save_wav(wav_path, waveform, sample_rate)

        try:
            # Convert float32 [-1, 1] → int16 PCM
            pcm_int16 = (waveform * 32767).clip(-32768, 32767).astype("int16")

            channels = 1 if pcm_int16.ndim == 1 else pcm_int16.shape[1]
            segment = AudioSegment(
                pcm_int16.tobytes(),
                frame_rate=sample_rate,
                sample_width=2,          # int16 = 2 bytes
                channels=channels,
            )
            path.parent.mkdir(parents=True, exist_ok=True)
            segment.export(str(path), format="mp3", bitrate="192k")
            log.info("Saved MP3 audio to %s", path)
            return True

        except Exception as exc:
            log.error("Failed to save MP3 audio to %s: %s", path, exc)
            # Last-resort fallback to WAV
            wav_path = path.with_suffix(".wav")
            log.warning("Falling back to WAV: %s", wav_path)
            return AudioManager._save_wav(wav_path, waveform, sample_rate)
