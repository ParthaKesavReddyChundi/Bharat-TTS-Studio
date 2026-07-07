"""
app/main.py
============
Bharat TTS Studio — application entry point.

Bootstraps:
  1. Python path / working directory (must be project root)
  2. Logging (before any other module uses get_logger)
  3. QApplication with HiDPI + font settings
  4. AppController (wires all services + shows MainWindow)
  5. Qt event loop

Usage:
    python app/main.py
    # or if installed:
    bharat-tts-studio
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Force UTF-8 mode on Windows so Indic script characters in log messages
# don't crash on cp1252 terminals.  Must be set before any I/O.
os.environ.setdefault("PYTHONUTF8", "1")


def _ensure_project_root() -> None:
    """
    Make sure the current working directory is the project root
    (the directory containing the `app/` package), so that relative
    paths like `config/settings.yaml` and `models/` resolve correctly.
    """
    # If launched as `python app/main.py` from project root, cwd is already correct.
    # If launched from inside `app/`, we go up one level.
    cwd = Path.cwd()
    if not (cwd / "config").exists() and (cwd.parent / "config").exists():
        os.chdir(cwd.parent)

    # Add project root to sys.path so `from app.xxx import` works
    project_root = Path.cwd()
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))


def main() -> None:
    _ensure_project_root()

    # ── Bootstrap logging BEFORE any other import that calls get_logger ───
    from app.core.logger import setup_logging  # noqa: PLC0415
    setup_logging(Path("logs"), console_level="INFO")

    from app.core.logger import get_logger  # noqa: PLC0415
    log = get_logger("main")
    log.info("=" * 60)
    log.info("Bharat TTS Studio starting up…")
    log.info("Python %s | CWD: %s", sys.version.split()[0], Path.cwd())

    # ── Dependency check ─────────────────────────────────────────────────
    _check_dependencies(log)

    # ── QApplication ─────────────────────────────────────────────────────
    from PySide6.QtWidgets import QApplication  # noqa: PLC0415
    from PySide6.QtCore import Qt  # noqa: PLC0415
    from PySide6.QtGui import QFont  # noqa: PLC0415

    QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps)

    app = QApplication(sys.argv)
    app.setApplicationName("Bharat TTS Studio")
    app.setApplicationVersion("0.1.0")
    app.setOrganizationName("BharatTTSStudio")

    # Set a clean default font (overridden by QSS font-family)
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    # ── AppController (owns MainWindow, wires all services) ───────────────
    from app.app_controller import AppController  # noqa: PLC0415
    controller = AppController(qapp=app)
    controller.show()

    log.info("Entering Qt event loop.")
    exit_code = app.exec()
    log.info("Qt event loop exited with code %d.", exit_code)
    sys.exit(exit_code)


def _check_dependencies(log) -> None:
    """
    Check for hard-required dependencies at startup.
    Prints a blocking error (not a Qt dialog — Qt isn't up yet) and exits
    if a critical package is missing.
    """
    missing = []

    try:
        import PySide6  # noqa: F401
    except ImportError:
        missing.append(("PySide6", "pip install PySide6"))

    try:
        import yaml  # noqa: F401
    except ImportError:
        missing.append(("PyYAML", "pip install PyYAML"))

    if missing:
        print("\n" + "=" * 60)
        print("ERROR: Required packages are missing:")
        for pkg, cmd in missing:
            print(f"  {pkg} — install with: {cmd}")
        print("=" * 60 + "\n")
        sys.exit(1)

    # Soft warnings (optional packages)
    try:
        import torch  # noqa: F401
        cuda_ok = torch.cuda.is_available()
        log.info("PyTorch %s | CUDA available: %s", torch.__version__, cuda_ok)
        if not cuda_ok:
            log.warning(
                "CUDA not available — inference will run on CPU. "
                "Install PyTorch with CUDA: "
                "pip install torch==2.3.1+cu121 --index-url https://download.pytorch.org/whl/cu121"
            )
    except ImportError:
        log.warning("PyTorch not installed — model inference unavailable until installed.")

    try:
        import pynvml  # noqa: F401
    except ImportError:
        log.debug("pynvml not installed — GPU stats will be unavailable (optional).")

    try:
        import psutil  # noqa: F401
    except ImportError:
        log.warning("psutil not installed — CPU/RAM stats will be unavailable.")


if __name__ == "__main__":
    main()
