"""
app/gui/workers.py
==================
QThread workers to handle heavy background tasks (like TTS inference)
without freezing the main GUI thread.
"""

import threading
import numpy as np
from PySide6.QtCore import QThread, Signal

from app.engine.inference_engine import InferenceEngine
from app.core.logger import get_logger

log = get_logger(__name__)


class InferenceWorker(QThread):
    """
    Worker thread that runs the InferenceEngine synthesize method.

    Cancellation is cooperative: call ``cancel()`` from the GUI thread
    (or via EventBus) to set the internal flag.  The worker checks the
    flag before starting synthesis and emits ``generation_cancelled``
    (via EventBus) instead of ``finished_signal`` when cancelled.
    No orphaned threads are left behind — the QThread is simply asked to
    quit and the Python-level synthesis never began.
    """

    # Signals to communicate with the main thread
    started_signal = Signal()
    finished_signal = Signal(np.ndarray, int)  # waveform, sample_rate
    error_signal = Signal(str)

    def __init__(
        self,
        engine: InferenceEngine,
        text: str,
        model_id: str,
        device: str,
        speaker_id: str | None = None,
    ) -> None:
        super().__init__()
        self.engine = engine
        self.text = text
        self.model_id = model_id
        self.device = device
        self.speaker_id = speaker_id

        # Thread-safe cancellation flag
        self._cancel_event = threading.Event()

        # Wire the EventBus cancel request signal so the GUI Cancel button works
        try:
            from app.event_bus import EventBus  # noqa: PLC0415
            EventBus.instance().generation_cancel_requested.connect(self.cancel)
        except Exception:  # noqa: BLE001
            pass

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def cancel(self) -> None:
        """
        Request a cooperative cancellation.
        Safe to call from any thread.
        """
        log.info("Cancellation requested for worker (model='%s').", self.model_id)
        self._cancel_event.set()

    # ------------------------------------------------------------------
    # QThread entry point
    # ------------------------------------------------------------------

    def run(self) -> None:
        """Executed when the thread starts."""
        self.started_signal.emit()

        if self._cancel_event.is_set():
            log.info("Worker cancelled before synthesis started.")
            self._emit_cancelled()
            return

        try:
            log.info("Worker starting synthesis for model '%s'", self.model_id)
            waveform, sr = self.engine.synthesize(
                text=self.text,
                primary_model_id=self.model_id,
                speaker_id=self.speaker_id,
                device=self.device,
            )

            if self._cancel_event.is_set():
                log.info("Worker cancelled after synthesis completed — discarding result.")
                self._emit_cancelled()
                return

            self.finished_signal.emit(waveform, sr)

        except Exception as exc:
            if self._cancel_event.is_set():
                # A cancel during model loading can surface as an exception; treat it cleanly.
                log.info("Worker exception during cancellation — treating as cancelled: %s", exc)
                self._emit_cancelled()
            else:
                log.error("Worker encountered an error: %s", exc, exc_info=True)
                self.error_signal.emit(str(exc))

        finally:
            # Always disconnect from the EventBus to prevent stale connections
            try:
                from app.event_bus import EventBus  # noqa: PLC0415
                EventBus.instance().generation_cancel_requested.disconnect(self.cancel)
            except Exception:  # noqa: BLE001
                pass

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _emit_cancelled(self) -> None:
        """Emit the EventBus cancelled signal and log cleanly."""
        try:
            from app.event_bus import EventBus  # noqa: PLC0415
            EventBus.instance().generation_cancelled.emit()
        except Exception:  # noqa: BLE001
            pass
        log.info("Worker cleanly cancelled for model '%s'.", self.model_id)
