"""
app/gui/home_page.py
====================
The main user interface for text-to-speech synthesis.
"""

from typing import Any
import numpy as np

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, 
    QPushButton, QComboBox, QLabel, QGroupBox, 
    QFileDialog, QMessageBox, QProgressBar
)
from PySide6.QtCore import Qt

from app.engine.inference_engine import InferenceEngine
from app.core.audio_manager import AudioManager
from app.core.logger import get_logger
from app.gui.workers import InferenceWorker

log = get_logger(__name__)


class HomePage(QWidget):
    """Main tab for synthesizing single TTS requests."""

    def __init__(self, engine, history_manager, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.engine = engine
        self.history = history_manager
        self.current_waveform: np.ndarray | None = None
        self.current_sr: int = 16000
        self.worker: InferenceWorker | None = None
        
        from app.utils.i18n_labels import get_language_name
        self.get_language_name = get_language_name
        
        self.setup_ui()
        self.populate_languages()

    def setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        # 1. Header
        header = QLabel("Text-to-Speech Studio")
        header.setObjectName("pageHeader")  # For stylesheet styling
        header.setStyleSheet("font-size: 24px; font-weight: bold; margin-bottom: 10px;")
        main_layout.addWidget(header)
        
        # 2. Text Input Area
        text_group = QGroupBox("Input Text")
        text_layout = QVBoxLayout(text_group)
        self.text_input = QTextEdit()
        self.text_input.setPlaceholderText("Enter text here (e.g., नमस्ते, मेरा नाम राम है)...")
        self.text_input.setMinimumHeight(150)
        text_layout.addWidget(self.text_input)
        main_layout.addWidget(text_group)
        
        # 3. Controls (Language, Model & Device)
        controls_layout = QHBoxLayout()
        
        self.lang_selector = QComboBox()
        self.lang_selector.setMinimumWidth(150)
        self.lang_selector.currentTextChanged.connect(self.on_language_changed)
        
        self.model_selector = QComboBox()
        self.model_selector.setMinimumWidth(200)
        self.model_selector.currentIndexChanged.connect(self.on_model_changed)
        
        self.speaker_selector = QComboBox()
        self.speaker_selector.setMinimumWidth(150)
        
        self.device_selector = QComboBox()
        self.device_selector.addItems(["cpu", "cuda"])
        
        controls_layout.addWidget(QLabel("Language:"))
        controls_layout.addWidget(self.lang_selector)
        controls_layout.addWidget(QLabel("Model:"))
        controls_layout.addWidget(self.model_selector)
        controls_layout.addWidget(QLabel("Speaker:"))
        controls_layout.addWidget(self.speaker_selector)
        controls_layout.addStretch()
        controls_layout.addWidget(QLabel("Device:"))
        controls_layout.addWidget(self.device_selector)
        
        main_layout.addLayout(controls_layout)
        
        # 4. Action Buttons
        actions_layout = QHBoxLayout()
        
        self.btn_generate = QPushButton("Generate")
        self.btn_generate.setMinimumHeight(40)
        self.btn_generate.clicked.connect(self.on_generate_clicked)
        self.btn_generate.setProperty("class", "primary") # Assuming custom styling
        
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setMinimumHeight(40)
        self.btn_cancel.setEnabled(False)  # Only active during generation
        self.btn_cancel.clicked.connect(self.on_cancel_clicked)
        self.btn_cancel.setToolTip("Stop the current generation")
        
        self.btn_play = QPushButton("Play")
        self.btn_play.setMinimumHeight(40)
        self.btn_play.setEnabled(False)
        self.btn_play.clicked.connect(self.on_play_clicked)
        
        self.btn_stop = QPushButton("Stop")
        self.btn_stop.setMinimumHeight(40)
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self.on_stop_clicked)
        
        self.btn_save = QPushButton("Save to Disk")
        self.btn_save.setMinimumHeight(40)
        self.btn_save.setEnabled(False)
        self.btn_save.clicked.connect(self.on_save_clicked)
        
        actions_layout.addWidget(self.btn_generate)
        actions_layout.addWidget(self.btn_cancel)
        actions_layout.addWidget(self.btn_play)
        actions_layout.addWidget(self.btn_stop)
        actions_layout.addWidget(self.btn_save)
        
        main_layout.addLayout(actions_layout)
        
        # 5. Progress/Status Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0) # Indeterminate mode
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("Ready.")
        self.status_label.setStyleSheet("color: #888;")
        main_layout.addWidget(self.status_label)
        
        main_layout.addStretch()

    def populate_languages(self) -> None:
        """Extract unique languages from all available models."""
        models = self.engine.model_manager.get_available_models()
        langs = set()
        for m in models:
            for lang in m.get("languages", []):
                langs.add(lang)
                
        self.lang_selector.blockSignals(True)
        self.lang_selector.clear()
        
        # Sort languages alphabetically by their display name
        sorted_langs = sorted(list(langs), key=lambda x: self.get_language_name(x))
        for lang in sorted_langs:
            self.lang_selector.addItem(self.get_language_name(lang), userData=lang)
            
        self.lang_selector.blockSignals(False)
        
        # Trigger initial population of models
        if self.lang_selector.count() > 0:
            self.on_language_changed(self.lang_selector.currentText())

    def on_language_changed(self, lang_display_name: str) -> None:
        """Filter models based on selected language."""
        lang_code = self.lang_selector.currentData()
        if not lang_code:
            return
            
        models = self.engine.model_manager.get_available_models()
        self.model_selector.clear()
        for m in models:
            if lang_code in m.get("languages", []):
                self.model_selector.addItem(m.get("name"), userData=m.get("id"))
                
        self.on_model_changed()
        
    def on_model_changed(self, index: int = -1) -> None:
        """Populate speakers based on selected model and language."""
        self.speaker_selector.clear()
        model_id = self.model_selector.currentData()
        lang_code = self.lang_selector.currentData()
        
        if not model_id or not lang_code:
            self.speaker_selector.addItem("Default", userData=None)
            self.speaker_selector.setEnabled(False)
            return
            
        models = self.engine.model_manager.get_available_models()
        model_config = next((m for m in models if m.get("id") == model_id), None)
        
        if model_config and "speakers" in model_config and lang_code in model_config["speakers"]:
            speakers = model_config["speakers"][lang_code]
            for spk in speakers:
                self.speaker_selector.addItem(spk.get("name"), userData=spk.get("id"))
            self.speaker_selector.setEnabled(True)
        else:
            self.speaker_selector.addItem("Default", userData=None)
            self.speaker_selector.setEnabled(False)
            
    def on_generate_clicked(self) -> None:
        text = self.text_input.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "Input Error", "Please enter some text to synthesize.")
            return
            
        model_id = self.model_selector.currentData()
        speaker_id = self.speaker_selector.currentData()
        device = self.device_selector.currentText()
        
        self.btn_generate.setEnabled(False)
        self.btn_cancel.setEnabled(True)   # enable Cancel during generation
        self.btn_play.setEnabled(False)
        self.btn_save.setEnabled(False)
        self.progress_bar.setVisible(True)
        
        # Note about downloading for the first time
        self.status_label.setText(f"Generating audio using {model_id}... (Note: First time usage requires a background download)")
        
        # Start Worker
        self.worker = InferenceWorker(self.engine, text, model_id, device, speaker_id=speaker_id)
        self.worker.finished_signal.connect(self.on_generation_finished)
        self.worker.error_signal.connect(self.on_generation_error)
        
        # Wire EventBus cancellation signal → re-enable UI
        from app.event_bus import EventBus
        EventBus.instance().generation_cancelled.connect(self._on_generation_cancelled)
        
        self.worker.start()
        
    def on_generation_finished(self, waveform: np.ndarray, sr: int) -> None:
        self.current_waveform = waveform
        self.current_sr = sr
        
        self.btn_generate.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        self.btn_play.setEnabled(True)
        self.btn_save.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.status_label.setText("Generation complete. Ready to play.")

        # Auto-save for History
        text = self.text_input.toPlainText().strip()
        model_id = self.model_selector.currentData() or "unknown"
        lang = self.lang_selector.currentData() or "en"
        
        from pathlib import Path
        import datetime
        from app.core.audio_manager import AudioManager
        
        history_dir = Path("outputs/history")
        history_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = history_dir / f"{model_id}_{timestamp}.wav"
        
        # Save to disk
        if AudioManager.save(str(filepath), waveform, sr):
            # Log to history manager
            self.history.add_record(text, model_id, lang, str(filepath))
            # Refresh history page using EventBus (if connected) or MainWindow can handle it
            from app.event_bus import EventBus
            EventBus.instance().history_updated.emit()
            EventBus.instance().toast_requested.emit("Added to History", "INFO")

    def on_generation_error(self, error_msg: str) -> None:
        self.btn_generate.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        self.progress_bar.setVisible(False)
        self.status_label.setText("Generation failed.")
        QMessageBox.critical(self, "Synthesis Error", f"An error occurred:\n{error_msg}")

    def on_cancel_clicked(self) -> None:
        """User pressed Cancel — request cooperative stop via EventBus."""
        if self.worker and self.worker.isRunning():
            log.info("User requested generation cancellation.")
            self.btn_cancel.setEnabled(False)
            self.status_label.setText("Cancelling generation...")
            from app.event_bus import EventBus
            EventBus.instance().generation_cancel_requested.emit()

    def _on_generation_cancelled(self) -> None:
        """Called by EventBus when the worker has cleanly halted."""
        self.btn_generate.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        self.progress_bar.setVisible(False)
        self.status_label.setText("Generation cancelled.")
        # Disconnect one-shot slot to avoid stale connections on next run
        try:
            from app.event_bus import EventBus
            EventBus.instance().generation_cancelled.disconnect(self._on_generation_cancelled)
        except Exception:  # noqa: BLE001
            pass
        
    def on_play_clicked(self) -> None:
        if self.current_waveform is not None:
            self.btn_stop.setEnabled(True)
            self.status_label.setText("Playing audio...")
            AudioManager.play(self.current_waveform, self.current_sr)
            # We don't block, so the user has to press Stop manually, 
            # or it stops when it ends. For a robust app, we'd poll or use a callback to re-disable Stop.
            
    def on_stop_clicked(self) -> None:
        AudioManager.stop()
        self.btn_stop.setEnabled(False)
        self.status_label.setText("Playback stopped.")
        
    def on_save_clicked(self) -> None:
        if self.current_waveform is None:
            return

        # Build file-type filter — MP3 requires pydub; always offer WAV
        from app.core.audio_manager import _HAS_PYDUB  # noqa: PLC0415
        if _HAS_PYDUB:
            file_filter = "WAV Audio (*.wav);;MP3 Audio (*.mp3);;All Files (*.*)"
        else:
            file_filter = "WAV Audio (*.wav);;All Files (*.*)"

        file_path, selected_filter = QFileDialog.getSaveFileName(
            self, "Save Audio", "", file_filter
        )
        if not file_path:
            return

        # If the user selected MP3 filter but didn't type the extension, add it
        if "MP3" in selected_filter and not file_path.lower().endswith(".mp3"):
            file_path += ".mp3"
        elif "WAV" in selected_filter and not file_path.lower().endswith(".wav"):
            file_path += ".wav"

        success = AudioManager.save(file_path, self.current_waveform, self.current_sr)
        if success:
            QMessageBox.information(self, "Success", f"Audio saved to {file_path}")
            self.status_label.setText(f"Saved to {file_path}")
        else:
            QMessageBox.critical(self, "Error", "Failed to save audio. Check logs.")
