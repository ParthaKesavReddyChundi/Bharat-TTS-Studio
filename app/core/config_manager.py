"""
app/core/config_manager.py
===========================
Reads, validates, and persists application settings.

On first run, copies settings.default.yaml → config/settings.yaml.
At runtime, reads from config/settings.yaml.

Usage:
    from app.core.config_manager import ConfigManager
    cfg = ConfigManager()
    theme = cfg.get("app.theme")          # "dark"
    cfg.set("app.theme", "light")
    cfg.save()
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import yaml

from app.core.exceptions import ConfigError
from app.core.logger import get_logger

log = get_logger(__name__)

# Paths are relative to the project root (where main.py is launched from).
_DEFAULT_SETTINGS_PATH = Path("config/settings.default.yaml")
_SETTINGS_PATH = Path("config/settings.yaml")


class ConfigManager:
    """
    Singleton-friendly settings manager.

    Loads YAML settings on construction, exposes dot-notation getters/setters,
    and persists changes back to disk.  Thread-safe for reads; callers should
    serialise writes if needed (settings are changed only in the UI thread).
    """

    def __init__(
        self,
        settings_path: Path | str = _SETTINGS_PATH,
        default_path: Path | str = _DEFAULT_SETTINGS_PATH,
    ) -> None:
        self._settings_path = Path(settings_path)
        self._default_path = Path(default_path)
        self._data: dict[str, Any] = {}
        self._load()

    # ── Public API ────────────────────────────────────────────────────────────

    def get(self, key: str, default: Any = None) -> Any:
        """
        Retrieve a setting by dot-notation key (e.g. ``"app.theme"``).

        Args:
            key:     Dot-separated path into the settings dict.
            default: Value returned if the key does not exist.

        Returns:
            The setting value, or *default* if not found.
        """
        parts = key.split(".")
        node: Any = self._data
        for part in parts:
            if not isinstance(node, dict) or part not in node:
                return default
            node = node[part]
        return node

    def set(self, key: str, value: Any) -> None:
        """
        Update a setting by dot-notation key.  Changes are in-memory only
        until :meth:`save` is called.

        Args:
            key:   Dot-separated path into the settings dict.
            value: New value to assign.
        """
        parts = key.split(".")
        node = self._data
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node[parts[-1]] = value
        log.debug("Config updated: %s = %r", key, value)

    def save(self) -> None:
        """Persist the current in-memory settings back to disk."""
        try:
            self._settings_path.parent.mkdir(parents=True, exist_ok=True)
            with self._settings_path.open("w", encoding="utf-8") as fh:
                yaml.dump(self._data, fh, allow_unicode=True, default_flow_style=False)
            log.debug("Settings saved to %s", self._settings_path)
        except OSError as exc:
            raise ConfigError(
                "Could not save settings.",
                details=str(exc),
            ) from exc

    def reload(self) -> None:
        """Re-read settings from disk (discards unsaved in-memory changes)."""
        self._load()

    @property
    def settings_path(self) -> Path:
        """Absolute path to the active settings file."""
        return self._settings_path.resolve()

    # ── Private ───────────────────────────────────────────────────────────────

    def _load(self) -> None:
        """Load settings from disk, bootstrapping from defaults if needed."""
        if not self._settings_path.exists():
            self._bootstrap_from_defaults()

        try:
            with self._settings_path.open("r", encoding="utf-8") as fh:
                data = yaml.safe_load(fh)
            if not isinstance(data, dict):
                raise ConfigError(
                    "settings.yaml is malformed (expected a YAML mapping).",
                    details=f"File: {self._settings_path}",
                )
            self._data = data
            log.info("Settings loaded from %s", self._settings_path)
        except yaml.YAMLError as exc:
            raise ConfigError(
                "settings.yaml contains invalid YAML.",
                details=str(exc),
            ) from exc

    def _bootstrap_from_defaults(self) -> None:
        """Copy settings.default.yaml → settings.yaml on first run."""
        if not self._default_path.exists():
            raise ConfigError(
                "Default settings file not found.",
                details=f"Expected: {self._default_path}",
            )
        self._settings_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(self._default_path, self._settings_path)
        log.info(
            "First run: bootstrapped settings from %s -> %s",
            self._default_path,
            self._settings_path,
        )
