"""
app/core/history_manager.py
============================
Manages generation history by saving records to a JSON file.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from datetime import datetime

from app.core.logger import get_logger

log = get_logger(__name__)


class HistoryManager:
    """Handles saving, loading, and deleting generation history."""

    def __init__(self, history_file: str | Path | None = None) -> None:
        if history_file is None:
            # Default to <project_root>/config/history.json
            self.history_file = Path(__file__).parents[2] / "config" / "history.json"
        else:
            self.history_file = Path(history_file)
            
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        self.records: list[dict[str, Any]] = self._load()

    def _load(self) -> list[dict[str, Any]]:
        if not self.history_file.exists():
            return []
        try:
            with open(self.history_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except Exception as exc:
            log.error("Failed to load history file: %s", exc)
            return []

    def _save(self) -> None:
        try:
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump(self.records, f, indent=4, ensure_ascii=False)
        except Exception as exc:
            log.error("Failed to save history file: %s", exc)

    def add_record(self, text: str, model_id: str, lang: str, filepath: str) -> dict[str, Any]:
        """Add a new generation record to history."""
        record = {
            "id": datetime.now().strftime("%Y%m%d_%H%M%S_%f"),
            "timestamp": datetime.now().isoformat(),
            "text": text,
            "model_id": model_id,
            "lang": lang,
            "filepath": str(filepath)
        }
        self.records.insert(0, record)  # Newest first
        self._save()
        log.info("Added history record for %s", filepath)
        return record

    def delete_record(self, record_id: str) -> bool:
        """Delete a record from history and attempt to delete the file."""
        for i, record in enumerate(self.records):
            if record.get("id") == record_id:
                # Try to delete the actual file
                filepath = Path(record.get("filepath", ""))
                if filepath.exists():
                    try:
                        filepath.unlink()
                        log.info("Deleted file %s", filepath)
                    except Exception as exc:
                        log.warning("Failed to delete file %s: %s", filepath, exc)
                
                # Remove from history list
                del self.records[i]
                self._save()
                return True
        return False

    def clear_all(self) -> None:
        """Clear all history (does NOT delete files by default)."""
        self.records.clear()
        self._save()
        
    def get_all(self) -> list[dict[str, Any]]:
        """Return all records."""
        return self.records
