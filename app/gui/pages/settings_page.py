"""
app/gui/pages/settings_page.py
================================
Settings page — preferences, hardware, cache, model downloads.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QComboBox, QGroupBox, QPushButton, QMessageBox
)

from app.core.logger import get_logger

log = get_logger(__name__)


class SettingsPage(QWidget):
    """App settings and preferences."""

    def __init__(self, config, theme_manager, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.config = config
        self.theme_manager = theme_manager
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # Header
        title = QLabel("⚙️  Settings")
        title.setObjectName("h1")
        layout.addWidget(title)
        
        # UI Preferences Group
        ui_group = QGroupBox("UI Preferences")
        ui_layout = QVBoxLayout(ui_group)
        ui_layout.setSpacing(15)
        ui_layout.setContentsMargins(15, 25, 15, 15)
        
        # Theme Selector
        theme_layout = QHBoxLayout()
        theme_label = QLabel("Application Theme:")
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["dark", "light"])
        
        # Set current theme
        current_theme = self.config.get("app.theme", "dark")
        index = self.theme_combo.findText(current_theme)
        if index >= 0:
            self.theme_combo.setCurrentIndex(index)
            
        self.theme_combo.currentTextChanged.connect(self._on_theme_changed)
        
        theme_layout.addWidget(theme_label)
        theme_layout.addWidget(self.theme_combo)
        theme_layout.addStretch()
        ui_layout.addLayout(theme_layout)
        
        layout.addWidget(ui_group)
        
        # System & Data Group
        sys_group = QGroupBox("System & Data")
        sys_layout = QVBoxLayout(sys_group)
        sys_layout.setSpacing(15)
        sys_layout.setContentsMargins(15, 25, 15, 15)
        
        clear_history_btn = QPushButton("Clear Generation History")
        clear_history_btn.setFixedWidth(200)
        clear_history_btn.clicked.connect(self._on_clear_history)
        sys_layout.addWidget(clear_history_btn)
        
        layout.addWidget(sys_group)
        layout.addStretch()

    def _on_theme_changed(self, theme_name: str) -> None:
        """Handle theme change."""
        self.config.set("app.theme", theme_name)
        self.config.save()
        self.theme_manager.apply_saved_theme()
        
        from app.event_bus import EventBus
        EventBus.instance().toast_requested.emit(f"Theme changed to {theme_name}", "INFO")

    def _on_setting_changed(self, key: str, value: str) -> None:
        """Handle arbitrary setting changes (like API keys)."""
        self.config.set(key, value)
        self.config.save()

    def _on_clear_history(self) -> None:
        reply = QMessageBox.question(
            self, "Clear History", 
            "Are you sure you want to clear all generation history? This will NOT delete the actual audio files.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            # We access history_manager via main window or import it
            # But the easiest way is just to load it briefly
            from app.core.history_manager import HistoryManager
            hm = HistoryManager()
            hm.clear_all()
            
            from app.event_bus import EventBus
            EventBus.instance().history_updated.emit()
            EventBus.instance().toast_requested.emit("History cleared", "INFO")
