"""
app/gui/pages/comparison_page.py
================================
Page for comparing multiple models side-by-side.
"""

from typing import Any
import numpy as np

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, 
    QPushButton, QComboBox, QLabel, QGroupBox, 
    QMessageBox, QProgressBar, QScrollArea, QFrame,
    QGridLayout, QTableWidget, QTableWidgetItem, QHeaderView,
    QCheckBox
)
from PySide6.QtCore import Qt, QThread, Signal

from app.engine.comparison_engine import ComparisonEngine, ComparisonResult
from app.core.audio_manager import AudioManager
from app.core.logger import get_logger

log = get_logger(__name__)

class ComparisonWorker(QThread):
    finished_signal = Signal(list)  # list[ComparisonResult]
    error_signal = Signal(str)

    def __init__(self, engine: ComparisonEngine, text: str, lang: str, models: list[str], device: str):
        super().__init__()
        self.engine = engine
        self.text = text
        self.lang = lang
        self.models = models
        self.device = device

    def run(self):
        try:
            results = self.engine.run_comparison(self.text, self.lang, self.models, self.device)
            self.finished_signal.emit(results)
        except Exception as e:
            self.error_signal.emit(str(e))


class ComparisonPage(QWidget):
    """Multi-model side-by-side comparison page."""

    def __init__(self, engine: Any = None) -> None:
        super().__init__()
        # We need a ComparisonEngine. We can instantiate it from the InferenceEngine's ModelManager
        # or it can be passed down. If an InferenceEngine was passed, we grab its ModelManager.
        model_manager = engine.model_manager if hasattr(engine, "model_manager") else None
        self.engine = ComparisonEngine(model_manager=model_manager)
        
        self.worker: ComparisonWorker | None = None
        self.current_results: list[ComparisonResult] = []
        
        from app.utils.i18n_labels import get_language_name
        self.get_language_name = get_language_name

        self.setup_ui()
        self.populate_languages()

    def setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Global Scroll Area to make the page scrollable
        global_scroll = QScrollArea()
        global_scroll.setWidgetResizable(True)
        global_scroll.setFrameShape(QFrame.NoFrame)
        
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(20, 20, 20, 20)
        scroll_layout.setSpacing(15)

        # Header
        header = QLabel("Model Comparison")
        header.setStyleSheet("font-size: 24px; font-weight: bold;")
        scroll_layout.addWidget(header)

        # Controls Group (Text, Lang, Device, Gen Button)
        controls_group = QGroupBox("Comparison Settings")
        controls_layout = QVBoxLayout(controls_group)
        
        self.text_input = QTextEdit()
        self.text_input.setPlaceholderText("Enter text to compare across models...")
        self.text_input.setMinimumHeight(80)
        controls_layout.addWidget(self.text_input)

        row_layout = QHBoxLayout()
        self.lang_selector = QComboBox()
        self.lang_selector.currentTextChanged.connect(self.on_language_changed)
        
        self.device_selector = QComboBox()
        self.device_selector.addItems(["cpu", "cuda"])

        row_layout.addWidget(QLabel("Language:"))
        row_layout.addWidget(self.lang_selector)
        row_layout.addStretch()
        row_layout.addWidget(QLabel("Device:"))
        row_layout.addWidget(self.device_selector)
        
        self.btn_generate = QPushButton("Generate All")
        self.btn_generate.setProperty("class", "primary")
        self.btn_generate.clicked.connect(self.on_generate_clicked)
        row_layout.addWidget(self.btn_generate)
        
        controls_layout.addLayout(row_layout)
        
        # Model checkboxes area
        self.models_widget = QWidget()
        self.models_layout = QHBoxLayout(self.models_widget)
        controls_layout.addWidget(QLabel("Select Models to Compare:"))
        controls_layout.addWidget(self.models_widget)

        scroll_layout.addWidget(controls_group)

        # Progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(False)
        scroll_layout.addWidget(self.progress_bar)

        # Results Grid (No inner scroll area to avoid nested scrollbars)
        self.results_container = QWidget()
        self.results_layout = QHBoxLayout(self.results_container)
        scroll_layout.addWidget(self.results_container)

        # Summary Table
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Model", "Status", "Latency (s)", "RTF", "Actions"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setMinimumHeight(200)
        scroll_layout.addWidget(self.table)
        
        self.status_label = QLabel("Ready.")
        scroll_layout.addWidget(self.status_label)
        
        global_scroll.setWidget(scroll_content)
        main_layout.addWidget(global_scroll)

    def populate_languages(self) -> None:
        models = self.engine.model_manager.get_available_models()
        langs = set()
        for m in models:
            for lang in m.get("languages", []):
                langs.add(lang)
                
        self.lang_selector.blockSignals(True)
        self.lang_selector.clear()
        
        sorted_langs = sorted(list(langs), key=lambda x: self.get_language_name(x))
        for lang in sorted_langs:
            self.lang_selector.addItem(self.get_language_name(lang), userData=lang)
            
        self.lang_selector.blockSignals(False)
        
        if self.lang_selector.count() > 0:
            self.on_language_changed(self.lang_selector.currentText())

    def on_language_changed(self, lang_display_name: str) -> None:
        lang_code = self.lang_selector.currentData()
        if not lang_code:
            return
            
        # Clear existing checkboxes
        while self.models_layout.count():
            item = self.models_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        models = self.engine.model_manager.get_available_models()
        self.model_checkboxes = []
        for m in models:
            if lang_code in m.get("languages", []):
                cb = QCheckBox(m.get("name"))
                cb.setProperty("model_id", m.get("id"))
                self.models_layout.addWidget(cb)
                self.model_checkboxes.append(cb)
                
        self.models_layout.addStretch()

    def on_generate_clicked(self) -> None:
        text = self.text_input.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "Input Error", "Please enter some text.")
            return
            
        selected_models = [cb.property("model_id") for cb in self.model_checkboxes if cb.isChecked()]
        if not selected_models:
            QMessageBox.warning(self, "Selection Error", "Please select at least one model to compare.")
            return

        lang_code = self.lang_selector.currentData()
        device = self.device_selector.currentText()
        
        self.btn_generate.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.status_label.setText(f"Comparing {len(selected_models)} models. This will take a moment...")
        
        # Clear results
        while self.results_layout.count():
            item = self.results_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.table.setRowCount(0)

        self.worker = ComparisonWorker(self.engine, text, lang_code, selected_models, device)
        self.worker.finished_signal.connect(self.on_comparison_finished)
        self.worker.error_signal.connect(self.on_comparison_error)
        self.worker.start()

    def on_comparison_finished(self, results: list[ComparisonResult]) -> None:
        self.btn_generate.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.status_label.setText("Comparison complete.")
        
        self.current_results = results
        self.table.setRowCount(len(results))
        
        for i, res in enumerate(results):
            # 1. Build Grid Card
            card = QFrame()
            card.setFrameShape(QFrame.StyledPanel)
            cl = QVBoxLayout(card)
            
            title = QLabel(res.model_id)
            title.setStyleSheet("font-weight: bold;")
            cl.addWidget(title)
            
            if res.error_msg:
                err = QLabel(f"Error: {res.error_msg}")
                err.setStyleSheet("color: red;")
                err.setWordWrap(True)
                cl.addWidget(err)
            else:
                btn_play = QPushButton("▶ Play")
                btn_play.clicked.connect(lambda checked=False, w=res.waveform, sr=res.sample_rate: AudioManager.play(w, sr))
                cl.addWidget(btn_play)
                
                btn_stop = QPushButton("⏹ Stop")
                btn_stop.clicked.connect(lambda checked=False: AudioManager.stop())
                cl.addWidget(btn_stop)
                
                cl.addWidget(QLabel(f"Latency: {res.latency_sec:.2f}s | RTF: {res.rtf:.2f}"))
                
            cl.addStretch()
            self.results_layout.addWidget(card)
            
            # 2. Populate Table
            self.table.setItem(i, 0, QTableWidgetItem(res.model_id))
            if res.error_msg:
                self.table.setItem(i, 1, QTableWidgetItem("Failed"))
                self.table.setItem(i, 2, QTableWidgetItem("-"))
                self.table.setItem(i, 3, QTableWidgetItem("-"))
            else:
                self.table.setItem(i, 1, QTableWidgetItem("Success"))
                self.table.setItem(i, 2, QTableWidgetItem(f"{res.latency_sec:.2f}s"))
                self.table.setItem(i, 3, QTableWidgetItem(f"{res.rtf:.2f}"))
                
            play_btn_tbl = QPushButton("Play")
            if res.error_msg:
                play_btn_tbl.setEnabled(False)
            else:
                play_btn_tbl.clicked.connect(lambda checked=False, w=res.waveform, sr=res.sample_rate: AudioManager.play(w, sr))
            self.table.setCellWidget(i, 4, play_btn_tbl)

    def on_comparison_error(self, error: str) -> None:
        self.btn_generate.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.status_label.setText("Comparison failed.")
        QMessageBox.critical(self, "Error", str(error))
