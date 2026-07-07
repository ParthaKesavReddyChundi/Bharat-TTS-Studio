"""
app/event_bus.py
================
Central publish/subscribe hub using Qt signals.

Instead of modules importing each other directly, they import EventBus
and connect to or emit named signals.  This keeps all cross-module
communication in one place and eliminates circular imports.

Usage:
    from app.event_bus import EventBus
    bus = EventBus.instance()

    # Emit
    bus.generation_complete.emit(result)

    # Subscribe
    bus.generation_complete.connect(my_slot)
"""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from app.core.logger import get_logger

log = get_logger(__name__)


class EventBus(QObject):
    """
    Application-wide Qt signal bus.

    One instance lives on the AppController and is passed down to every
    service that needs to communicate cross-module.
    """

    # ── Generation signals ────────────────────────────────────────────────────
    # Emitted when inference completes successfully.
    # Payload: dict with keys: audio_path, sample_rate, metrics, model_id, lang, text
    generation_complete = Signal(dict)

    # Emitted when inference fails.
    # Payload: str (user-facing error message), str (technical details for log)
    generation_failed = Signal(str, str)

    # Emitted periodically during generation to report progress (0.0–1.0).
    generation_progress = Signal(float)

    # ── Comparison signals ────────────────────────────────────────────────────
    # Emitted when one model in a comparison batch finishes.
    # Payload: dict (same structure as generation_complete, plus 'model_id')
    comparison_item_complete = Signal(dict)

    # Emitted when the full comparison batch is done.
    # Payload: list[dict]
    comparison_complete = Signal(list)

    comparison_failed = Signal(str, str)

    # ── Model management signals ──────────────────────────────────────────────
    # Emitted when a model finishes loading into memory.
    # Payload: str (model_id)
    model_loaded = Signal(str)

    # Emitted when a model is evicted from memory.
    # Payload: str (model_id)
    model_unloaded = Signal(str)

    # Emitted periodically during model download (0.0–1.0).
    download_progress = Signal(str, float)   # model_id, fraction

    # Emitted when a model download completes.
    # Payload: str (model_id)
    download_complete = Signal(str)

    download_failed = Signal(str, str)       # model_id, error message

    # ── System info signals ───────────────────────────────────────────────────
    # Emitted by SystemMonitorWorker with a fresh SystemSnapshot.
    system_snapshot = Signal(object)         # SystemSnapshot dataclass

    # ── Global error signal ───────────────────────────────────────────────────
    # Any unhandled TTSStudioError from any worker lands here.
    # Payload: str (user message), str (technical details)
    error_occurred = Signal(str, str)

    # ── UI state signals ──────────────────────────────────────────────────────
    # Request the GUI to show a toast notification.
    # Payload: str (message), str (level: "info" | "warning" | "error")
    toast_requested = Signal(str, str)
    
    # Emitted when a new history record is added
    history_updated = Signal()

    # ── Singleton ─────────────────────────────────────────────────────────────
    _instance: EventBus | None = None

    @classmethod
    def instance(cls) -> "EventBus":
        """Return the application-wide singleton EventBus."""
        if cls._instance is None:
            cls._instance = cls()
            log.debug("EventBus singleton created.")
        return cls._instance
