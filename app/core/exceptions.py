"""
app/core/exceptions.py
======================
Custom exception hierarchy for Bharat TTS Studio.

All application-level exceptions inherit from TTSStudioError.
Worker boundaries catch these and re-emit them as typed Qt signals
so the GUI can react appropriately — no raw tracebacks shown to users.
"""


class TTSStudioError(Exception):
    """Base exception for all Bharat TTS Studio errors."""

    def __init__(self, message: str, details: str = "") -> None:
        super().__init__(message)
        self.message = message
        self.details = details  # Full technical detail, goes to log only

    def __str__(self) -> str:
        return self.message


# ── Configuration errors ──────────────────────────────────────────────────────

class ConfigError(TTSStudioError):
    """Raised when settings YAML cannot be loaded or validated."""


class CatalogError(TTSStudioError):
    """Raised when models_catalog.yaml or languages_catalog.yaml is malformed."""


# ── Model management errors ───────────────────────────────────────────────────

class ModelNotFoundError(TTSStudioError):
    """Model checkpoint files do not exist on disk."""

    def __init__(self, model_id: str, path: str = "") -> None:
        super().__init__(
            f"Model '{model_id}' is not downloaded.",
            details=f"Expected path: {path}",
        )
        self.model_id = model_id
        self.path = path


class ModelCorruptedError(TTSStudioError):
    """Model checkpoint failed checksum or format validation."""

    def __init__(self, model_id: str, reason: str = "") -> None:
        super().__init__(
            f"Model '{model_id}' appears to be corrupted.",
            details=reason,
        )
        self.model_id = model_id


class ModelLoadError(TTSStudioError):
    """Model weights could not be loaded by the adapter."""

    def __init__(self, model_id: str, reason: str = "") -> None:
        super().__init__(
            f"Failed to load model '{model_id}'.",
            details=reason,
        )
        self.model_id = model_id


class OutOfMemoryError(TTSStudioError):  # noqa: A001
    """Insufficient VRAM/RAM to load the requested model."""

    def __init__(self, model_id: str, required_gb: float, available_gb: float) -> None:
        super().__init__(
            f"Not enough memory to load '{model_id}' "
            f"(needs ~{required_gb:.1f} GB, ~{available_gb:.1f} GB available).",
        )
        self.model_id = model_id
        self.required_gb = required_gb
        self.available_gb = available_gb


class DownloadError(TTSStudioError):
    """Model download failed (network error, 404, checksum mismatch)."""

    def __init__(self, model_id: str, reason: str = "") -> None:
        super().__init__(
            f"Failed to download model '{model_id}'.",
            details=reason,
        )
        self.model_id = model_id


# ── Inference errors ──────────────────────────────────────────────────────────

class InferenceError(TTSStudioError):
    """Synthesis failed inside an adapter."""

    def __init__(self, model_id: str, reason: str = "") -> None:
        super().__init__(
            f"Inference failed for model '{model_id}'.",
            details=reason,
        )
        self.model_id = model_id


class UnsupportedLanguageError(TTSStudioError):
    """The selected model does not support the chosen language."""

    def __init__(self, model_id: str, lang_code: str) -> None:
        super().__init__(
            f"Model '{model_id}' does not support language '{lang_code}'.",
        )
        self.model_id = model_id
        self.lang_code = lang_code


class UnsupportedSpeakerError(TTSStudioError):
    """The requested speaker ID is not valid for this model + language combo."""

    def __init__(self, model_id: str, speaker_id: str) -> None:
        super().__init__(
            f"Speaker '{speaker_id}' is not available in model '{model_id}'.",
        )
        self.model_id = model_id
        self.speaker_id = speaker_id


# ── Preprocessing errors ──────────────────────────────────────────────────────

class PreprocessingError(TTSStudioError):
    """Text normalization pipeline encountered an unrecoverable error."""


class InvalidInputError(TTSStudioError):
    """User-supplied text is empty or contains only invalid characters."""


# ── Audio errors ──────────────────────────────────────────────────────────────

class AudioPlaybackError(TTSStudioError):
    """Audio output device failed or became unavailable."""


class AudioSaveError(TTSStudioError):
    """Could not write WAV file to disk."""


# ── Dependency errors ─────────────────────────────────────────────────────────

class MissingDependencyError(TTSStudioError):
    """A required Python package is not installed."""

    def __init__(self, package: str, pip_command: str = "") -> None:
        super().__init__(
            f"Required package '{package}' is not installed.",
            details=f"Install with: {pip_command}" if pip_command else "",
        )
        self.package = package
        self.pip_command = pip_command
