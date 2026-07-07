"""
app/gui/workers.py
==================
QThread workers to handle heavy background tasks (like TTS inference)
without freezing the main GUI thread.
"""

import numpy as np
from PySide6.QtCore import QThread, Signal

from app.engine.inference_engine import InferenceEngine
from app.core.logger import get_logger

log = get_logger(__name__)


class InferenceWorker(QThread):
    """
    Worker thread that runs the InferenceEngine synthesize method.
    """
    
    # Signals to communicate with the main thread
    started_signal = Signal()
    finished_signal = Signal(np.ndarray, int)  # waveform, sample_rate
    error_signal = Signal(str)

    def __init__(self, engine: InferenceEngine, text: str, model_id: str, device: str, speaker_id: str | None = None) -> None:
        super().__init__()
        self.engine = engine
        self.text = text
        self.model_id = model_id
        self.device = device
        self.speaker_id = speaker_id
        
    def run(self) -> None:
        """Executed when the thread starts."""
        self.started_signal.emit()
        try:
            log.info("Worker starting synthesis for model '%s'", self.model_id)
            waveform, sr = self.engine.synthesize(
                text=self.text,
                primary_model_id=self.model_id,
                speaker_id=self.speaker_id,
                device=self.device
            )
            self.finished_signal.emit(waveform, sr)
        except Exception as exc:
            log.error("Worker encountered an error: %s", exc, exc_info=True)
            self.error_signal.emit(str(exc))
