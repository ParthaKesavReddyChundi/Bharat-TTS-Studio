"""
app/app_controller.py
======================
Top-level application orchestrator.

Owns:
  - ConfigManager
  - ThemeManager
  - EventBus reference
  - MainWindow reference
  - Startup sequence (async system probe)

Architectural rule: AppController wires GUI events to service calls.
It must NOT contain preprocessing/model/DSP logic itself.

Phase 1: Stub — initialises core services and owns MainWindow lifecycle.
Phase 4+: Will wire inference/audio/cache services.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from app.core.config_manager import ConfigManager
from app.core.logger import get_logger, setup_logging
from app.event_bus import EventBus
from app.engine.inference_engine import InferenceEngine

log = get_logger(__name__)


class AppController:
    """
    Wires all services together and drives the application lifecycle.

    Instantiated once from main.py after QApplication is created.
    """

    def __init__(self, qapp: QApplication) -> None:
        self._qapp = qapp

        # ── Core services ─────────────────────────────────────────────────
        self._config = ConfigManager()

        # Re-configure logging now that we have the config-specified level
        log_level = self._config.get("app.log_level", "INFO")
        setup_logging(Path("logs"), console_level=log_level)

        self._bus = EventBus.instance()

        # ── Theme ─────────────────────────────────────────────────────────
        from app.gui.theme.theme_manager import ThemeManager  # noqa: PLC0415
        self._theme_manager = ThemeManager(app=qapp, config=self._config)
        self._theme_manager.apply_saved_theme()

        from app.core.history_manager import HistoryManager  # noqa: PLC0415
        self._history_manager = HistoryManager()

        # ── Main window ───────────────────────────────────────────────────
        from app.gui.main_window import MainWindow  # noqa: PLC0415
        
        self.engine = InferenceEngine()
        
        self._window = MainWindow(
            config=self._config,
            theme_manager=self._theme_manager,
            engine=self.engine,
            history_manager=self._history_manager
        )

        # ── Connect global error signal to status bar ─────────────────────
        self._bus.error_occurred.connect(self._on_error)
        self._bus.toast_requested.connect(self._on_toast)

        log.info("AppController initialised.")

    def show(self) -> None:
        """Display the main window and kick off async startup tasks."""
        self._window.show()

        # Defer system probe to after the event loop starts (non-blocking).
        QTimer.singleShot(200, self._async_startup)

    # ── Private ───────────────────────────────────────────────────────────────

    def _async_startup(self) -> None:
        """
        Runs shortly after the window appears.
        Probes hardware and updates the status bar.
        Phase 1: simple synchronous probe; Phase 4+ moves to a worker.
        """
        try:
            from app.core import system_monitor  # noqa: PLC0415
            snap = system_monitor.probe()

            if snap.gpu_available:
                gpu_text = f"GPU: {snap.gpu_name} ({snap.vram_used_gb:.1f}/{snap.vram_total_gb:.1f} GB)"
                if snap.cuda_available:
                    gpu_text += " ● CUDA"
            elif snap.cuda_available:
                gpu_text = "CUDA available (GPU stats unavailable)"
            else:
                gpu_text = "CPU mode (no CUDA)"

            self._window.update_gpu_label(gpu_text)
            self._window.update_status("Ready")
            log.info("Hardware probe complete: %s", gpu_text)
        except Exception as exc:  # noqa: BLE001
            log.warning("Hardware probe failed: %s", exc)
            self._window.update_gpu_label("Hardware detection failed")

    def _on_error(self, message: str, details: str) -> None:
        """Global error handler — updates status bar and logs."""
        self._window.update_status(f"Error: {message}")
        if details:
            log.error("%s | %s", message, details)
        else:
            log.error("%s", message)

    def _on_toast(self, message: str, level: str) -> None:
        """Route toast requests to the status bar in Phase 1 (full toast in Phase 5)."""
        self._window.update_status(message)
        log.info("Toast [%s]: %s", level, message)
