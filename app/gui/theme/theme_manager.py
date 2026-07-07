"""
app/gui/theme/theme_manager.py
===============================
Runtime theme switcher.

Loads dark_theme.qss or light_theme.qss and applies it to the
QApplication instance.  Persists the chosen theme to ConfigManager.

Usage:
    from app.gui.theme.theme_manager import ThemeManager
    tm = ThemeManager(app=qapp, config=cfg)
    tm.apply_theme("dark")
    tm.toggle()
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QApplication

from app.core.config_manager import ConfigManager
from app.core.logger import get_logger

log = get_logger(__name__)

_THEME_DIR = Path(__file__).parent
_THEME_FILES: dict[str, Path] = {
    "dark": _THEME_DIR / "dark_theme.qss",
    "light": _THEME_DIR / "light_theme.qss",
}


class ThemeManager:
    """Applies and switches QSS themes at runtime."""

    def __init__(self, app: QApplication, config: ConfigManager) -> None:
        self._app = app
        self._config = config
        self._current_theme: str = config.get("app.theme", "dark")

    # ── Public API ────────────────────────────────────────────────────────────

    @property
    def current_theme(self) -> str:
        return self._current_theme

    def apply_theme(self, theme: str) -> None:
        """
        Apply *theme* ("dark" or "light") to the QApplication.

        Args:
            theme: Theme name.  Falls back to "dark" if unknown.
        """
        theme = theme.lower()
        if theme not in _THEME_FILES:
            log.warning("Unknown theme '%s', falling back to 'dark'.", theme)
            theme = "dark"

        qss_path = _THEME_FILES[theme]
        if not qss_path.exists():
            log.error("Theme file not found: %s", qss_path)
            return

        try:
            stylesheet = qss_path.read_text(encoding="utf-8")
            self._app.setStyleSheet(stylesheet)
            self._current_theme = theme
            self._config.set("app.theme", theme)
            log.info("Theme applied: %s", theme)
        except OSError as exc:
            log.error("Failed to load theme file %s: %s", qss_path, exc)

    def toggle(self) -> str:
        """
        Switch between dark and light themes.

        Returns:
            The name of the newly active theme.
        """
        next_theme = "light" if self._current_theme == "dark" else "dark"
        self.apply_theme(next_theme)
        return next_theme

    def apply_saved_theme(self) -> None:
        """Apply whatever theme is stored in ConfigManager."""
        saved = self._config.get("app.theme", "dark")
        self.apply_theme(saved)
