"""
app/gui/main_window.py
=======================
QMainWindow — the top-level application shell.

Hosts:
  - Menu bar (File, View, Help)
  - Central QTabWidget with stub pages: Home | Compare | History | Settings
  - Status bar (ready state, last-gen time, GPU indicator)
  - Theme toggle action

Architectural rule: MainWindow contains ZERO business logic.
It only creates layout + widgets and wires Qt signals from/to AppController.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QFont, QIcon
from PySide6.QtWidgets import (
    QLabel,
    QMainWindow,
    QStatusBar,
    QTabWidget,
    QWidget,
)

from app.core.logger import get_logger

log = get_logger(__name__)


class MainWindow(QMainWindow):
    """Application shell window."""

    def __init__(
        self,
        config: Any,
        theme_manager: Any,
        engine: Any,
        history_manager: Any,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._config = config
        self._theme = theme_manager
        self._engine = engine
        self._history = history_manager

        self._setup_window()
        self._build_menu_bar()
        self._build_central_tabs()
        self._build_status_bar()

        log.info("MainWindow initialised.")

    # ── Window setup ──────────────────────────────────────────────────────────

    def _setup_window(self) -> None:
        self.setWindowTitle("Bharat TTS Studio")
        self.setMinimumSize(1100, 700)

        # Restore saved geometry
        width = 1400
        height = 860
        if self._config:
            width = self._config.get("app.window_width", 1400)
            height = self._config.get("app.window_height", 860)
        self.resize(width, height)

        # Centre on screen
        screen = self.screen()
        if screen:
            geo = screen.availableGeometry()
            self.move(
                (geo.width() - self.width()) // 2,
                (geo.height() - self.height()) // 2,
            )

    # ── Menu bar ──────────────────────────────────────────────────────────────

    def _build_menu_bar(self) -> None:
        mb = self.menuBar()

        # File
        file_menu = mb.addMenu("&File")
        self._act_save_wav = QAction("Save WAV…", self)
        self._act_save_wav.setShortcut("Ctrl+S")
        self._act_save_wav.setEnabled(False)
        file_menu.addAction(self._act_save_wav)
        file_menu.addSeparator()
        act_quit = QAction("&Quit", self)
        act_quit.setShortcut("Ctrl+Q")
        act_quit.triggered.connect(self.close)
        file_menu.addAction(act_quit)

        # View
        view_menu = mb.addMenu("&View")
        act_toggle_theme = QAction("Toggle Dark/Light Theme", self)
        act_toggle_theme.setShortcut("Ctrl+T")
        act_toggle_theme.triggered.connect(self._on_toggle_theme)
        view_menu.addAction(act_toggle_theme)

        # Help
        help_menu = mb.addMenu("&Help")
        act_about = QAction("About Bharat TTS Studio", self)
        act_about.triggered.connect(self._on_about)
        help_menu.addAction(act_about)

    # ── Central tab widget ────────────────────────────────────────────────────

    def _build_central_tabs(self) -> None:
        self._tabs = QTabWidget()
        self._tabs.setDocumentMode(True)
        self._tabs.setTabPosition(QTabWidget.TabPosition.North)

        # Import pages lazily to avoid circular imports at module level.
        # Phase 1: stub placeholder widgets.
        from app.gui.pages.home_page import HomePage  # noqa: PLC0415
        from app.gui.pages.comparison_page import ComparisonPage  # noqa: PLC0415
        from app.gui.pages.history_page import HistoryPage  # noqa: PLC0415
        from app.gui.pages.settings_page import SettingsPage  # noqa: PLC0415

        self._home_page = HomePage(self._engine, self._history)
        self._compare_page = ComparisonPage(self._engine)
        self._history_page = HistoryPage(self._history)
        self._history_page.play_requested.connect(self._play_history_audio)
        self._settings_page = SettingsPage(self._config, self._theme)

        self._tabs.addTab(self._home_page, "🏠  Home")
        self._tabs.addTab(self._compare_page, "⚖️  Compare")
        self._tabs.addTab(self._history_page, "📜  History")
        self._tabs.addTab(self._settings_page, "⚙️  Settings")

        self.setCentralWidget(self._tabs)

    # ── Status bar ────────────────────────────────────────────────────────────

    def _build_status_bar(self) -> None:
        sb = QStatusBar()
        self.setStatusBar(sb)

        self._status_label = QLabel("Ready")
        self._status_label.setObjectName("statusLabel")
        sb.addWidget(self._status_label)

        # Spacer
        sb.addPermanentWidget(QLabel(""), 1)

        # GPU indicator (updated later by system monitor signal)
        self._gpu_label = QLabel("Detecting hardware…")
        self._gpu_label.setObjectName("gpuLabel")
        sb.addPermanentWidget(self._gpu_label)

        self._version_label = QLabel("v0.1.0 · Phase 1")
        font = QFont()
        font.setPointSize(10)
        self._version_label.setFont(font)
        sb.addPermanentWidget(self._version_label)

    # ── Public slots (called by AppController) ────────────────────────────────

    def update_status(self, message: str) -> None:
        """Update the main status bar text."""
        self._status_label.setText(message)

    def update_gpu_label(self, text: str) -> None:
        """Update the GPU memory indicator in the status bar."""
        self._gpu_label.setText(text)

    def _play_history_audio(self, filepath: str) -> None:
        from app.core.audio_manager import AudioManager
        import soundfile as sf
        import os
        from app.event_bus import EventBus
        
        if not os.path.exists(filepath):
            EventBus.instance().toast_requested.emit("File not found on disk.", "ERROR")
            return
            
        try:
            waveform, sr = sf.read(filepath)
            AudioManager.play(waveform, sr)
            EventBus.instance().toast_requested.emit("Playing history audio...", "INFO")
        except Exception as e:
            EventBus.instance().toast_requested.emit(f"Playback failed: {e}", "ERROR")

    def set_save_wav_enabled(self, enabled: bool) -> None:
        """Enable/disable the Save WAV menu action."""
        self._act_save_wav.setEnabled(enabled)

    # ── Private slots ─────────────────────────────────────────────────────────

    def _on_toggle_theme(self) -> None:
        if self._theme_manager:
            new_theme = self._theme_manager.toggle()
            if self._config:
                self._config.save()
            log.info("Theme toggled to: %s", new_theme)

    def _on_about(self) -> None:
        from PySide6.QtWidgets import QMessageBox  # noqa: PLC0415
        QMessageBox.about(
            self,
            "About Bharat TTS Studio",
            "<h3>Bharat TTS Studio v0.1.0</h3>"
            "<p>A fully local, offline desktop playground for comparing "
            "Indian Text-to-Speech models.</p>"
            "<p>Built with PySide6 · Python · PyTorch</p>",
        )

    # ── Window close ──────────────────────────────────────────────────────────

    def closeEvent(self, event) -> None:  # noqa: N802
        if self._config:
            self._config.set("app.window_width", self.width())
            self._config.set("app.window_height", self.height())
            self._config.save()
        log.info("Application closing.")
        super().closeEvent(event)
