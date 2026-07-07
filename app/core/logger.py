"""
app/core/logger.py
==================
Structured, rotating-file logger for Bharat TTS Studio.

Provides a factory function `get_logger(name)` used across all modules.
Logs simultaneously to:
  - A rotating file in logs/ (always at DEBUG level)
  - stdout (at the level configured in settings)
  - An in-memory deque that the LogConsolePanel reads from

Usage:
    from app.core.logger import get_logger
    log = get_logger(__name__)
    log.info("Model loaded in %.2fs", elapsed)
"""

from __future__ import annotations

import logging
import logging.handlers
import sys
from collections import deque
from pathlib import Path
from typing import Deque

# ── In-memory ring buffer shared with the GUI log console ─────────────────────
_LOG_BUFFER: Deque[logging.LogRecord] = deque(maxlen=1000)


class _BufferHandler(logging.Handler):
    """Appends every log record to the shared in-memory deque."""

    def emit(self, record: logging.LogRecord) -> None:
        _LOG_BUFFER.append(record)


def get_log_buffer() -> Deque[logging.LogRecord]:
    """Return the shared in-memory log buffer (read by LogConsolePanel)."""
    return _LOG_BUFFER


# ── Module-level state ────────────────────────────────────────────────────────
_initialized: bool = False
_log_dir: Path = Path("logs")


def setup_logging(log_dir: Path | str, console_level: str = "INFO") -> None:
    """
    Initialize the root logger.  Call this once from main.py before any
    other module uses get_logger().

    Args:
        log_dir:       Directory for rotating log files (created if missing).
        console_level: Log level for stdout output (DEBUG/INFO/WARNING/ERROR).
    """
    global _initialized, _log_dir

    _log_dir = Path(log_dir)
    _log_dir.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)  # capture everything; handlers filter

    if _initialized:
        return  # avoid duplicate handlers on re-import

    fmt = logging.Formatter(
        fmt="%(asctime)s [%(levelname)-8s] %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # ── Rotating file handler (always DEBUG) ──────────────────────────────
    log_file = _log_dir / "bharat_tts_studio.log"
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=5 * 1024 * 1024,  # 5 MB per file
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(fmt)
    root.addHandler(file_handler)

    # ── stdout handler (configurable level) ──────────────────────
    # Force UTF-8 on Windows (default cp1252 breaks Indic script log messages)
    import io  # noqa: PLC0415
    utf8_stdout = io.TextIOWrapper(
        sys.stdout.buffer,
        encoding="utf-8",
        errors="replace",
        line_buffering=True,
    ) if hasattr(sys.stdout, "buffer") else sys.stdout
    stdout_handler = logging.StreamHandler(utf8_stdout)
    stdout_handler.setLevel(getattr(logging, console_level.upper(), logging.INFO))
    stdout_handler.setFormatter(fmt)
    root.addHandler(stdout_handler)

    # ── In-memory buffer handler (for GUI log console) ─────────────────
    buffer_handler = _BufferHandler()
    buffer_handler.setLevel(logging.DEBUG)
    root.addHandler(buffer_handler)

    _initialized = True


def get_logger(name: str) -> logging.Logger:
    """
    Return a named logger.  Always call setup_logging() first from main.py.

    Args:
        name: Typically __name__ of the calling module.

    Returns:
        A standard library Logger instance.
    """
    return logging.getLogger(name)
