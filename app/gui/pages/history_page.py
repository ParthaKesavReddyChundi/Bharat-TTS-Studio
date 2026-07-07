"""
app/gui/pages/history_page.py
==============================
History page — browsable recent generations.
"""

from __future__ import annotations

import os
from pathlib import Path
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon, QDesktopServices
from PySide6.QtCore import QUrl
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QTableWidget, QTableWidgetItem, QPushButton, 
    QHeaderView, QMessageBox, QAbstractItemView
)

from app.core.logger import get_logger

log = get_logger(__name__)


class HistoryPage(QWidget):
    """Generation history browser."""
    
    play_requested = Signal(str)  # Emits filepath to play

    def __init__(self, history_manager, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.history_manager = history_manager
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Header
        header_layout = QHBoxLayout()
        title = QLabel("📜  Generation History")
        title.setObjectName("h1")
        header_layout.addWidget(title)
        
        refresh_btn = QPushButton("Refresh")
        refresh_btn.setFixedWidth(100)
        refresh_btn.clicked.connect(self.refresh_table)
        header_layout.addWidget(refresh_btn, alignment=Qt.AlignmentFlag.AlignRight)
        
        layout.addLayout(header_layout)

        # Table
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Date", "Model", "Language", "Text Snippet", "Actions"])
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setVisible(False)
        
        layout.addWidget(self.table)
        
        from app.event_bus import EventBus
        EventBus.instance().history_updated.connect(self.refresh_table)
        
        self.refresh_table()

    def refresh_table(self) -> None:
        """Reload data from HistoryManager into the table."""
        records = self.history_manager.get_all()
        self.table.setRowCount(len(records))
        
        for row, record in enumerate(records):
            # Date
            date_str = record.get("timestamp", "")[:16].replace("T", " ")
            self.table.setItem(row, 0, QTableWidgetItem(date_str))
            
            # Model
            self.table.setItem(row, 1, QTableWidgetItem(record.get("model_id", "")))
            
            # Language
            self.table.setItem(row, 2, QTableWidgetItem(record.get("lang", "").upper()))
            
            # Text Snippet
            text = record.get("text", "")
            snippet = text if len(text) < 40 else text[:37] + "..."
            self.table.setItem(row, 3, QTableWidgetItem(snippet))
            
            # Actions (Play, Folder, Delete)
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(4, 4, 4, 4)
            actions_layout.setSpacing(4)
            
            filepath = record.get("filepath", "")
            record_id = record.get("id", "")
            
            play_btn = QPushButton("▶")
            play_btn.setToolTip("Play Audio")
            play_btn.setFixedSize(28, 28)
            play_btn.clicked.connect(lambda _, fp=filepath: self.play_requested.emit(fp))
            
            folder_btn = QPushButton("📁")
            folder_btn.setToolTip("Open Folder")
            folder_btn.setFixedSize(28, 28)
            folder_btn.clicked.connect(lambda _, fp=filepath: self._open_folder(fp))
            
            del_btn = QPushButton("🗑")
            del_btn.setToolTip("Delete Record & File")
            del_btn.setFixedSize(28, 28)
            del_btn.setStyleSheet("background-color: #e74c3c; color: white;")
            del_btn.clicked.connect(lambda _, rid=record_id: self._delete_record(rid))
            
            actions_layout.addWidget(play_btn)
            actions_layout.addWidget(folder_btn)
            actions_layout.addWidget(del_btn)
            actions_layout.addStretch()
            
            self.table.setCellWidget(row, 4, actions_widget)
            
            # Set row height
            self.table.setRowHeight(row, 40)

    def _open_folder(self, filepath: str) -> None:
        """Open the folder containing the generated audio."""
        if os.path.exists(filepath):
            folder = os.path.dirname(filepath)
            QDesktopServices.openUrl(QUrl.fromLocalFile(folder))
        else:
            QMessageBox.warning(self, "File Not Found", f"The file no longer exists at:\n{filepath}")

    def _delete_record(self, record_id: str) -> None:
        """Confirm and delete a history record."""
        reply = QMessageBox.question(
            self, "Confirm Delete", 
            "Are you sure you want to delete this generation? The audio file will also be deleted.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            success = self.history_manager.delete_record(record_id)
            if success:
                self.refresh_table()
            else:
                QMessageBox.warning(self, "Error", "Failed to delete the record.")
