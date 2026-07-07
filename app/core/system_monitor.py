"""
app/core/system_monitor.py
===========================
Asynchronous CPU / GPU / RAM / VRAM probing.

Provides a snapshot dataclass and a background-safe probe function.
The GUI reads from this via the Qt signal emitted by AppController —
this module itself has NO Qt dependency (keeps it unit-testable).

Optional dependencies (gracefully absent):
  - pynvml  : NVIDIA GPU stats (VRAM usage, GPU utilisation %)
  - psutil  : CPU / RAM stats (almost always available)
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional

from app.core.logger import get_logger

log = get_logger(__name__)

# ── Optional imports ──────────────────────────────────────────────────────────
try:
    import psutil
    _PSUTIL_AVAILABLE = True
except ImportError:
    psutil = None  # type: ignore[assignment]
    _PSUTIL_AVAILABLE = False
    log.warning("psutil not installed — CPU/RAM stats unavailable.")

try:
    import pynvml
    pynvml.nvmlInit()
    _PYNVML_AVAILABLE = True
    log.info("pynvml initialised — NVIDIA GPU stats enabled.")
except Exception:  # noqa: BLE001
    pynvml = None  # type: ignore[assignment]
    _PYNVML_AVAILABLE = False
    log.info("pynvml not available or no NVIDIA GPU — GPU stats disabled.")


@dataclass
class SystemSnapshot:
    """Immutable point-in-time snapshot of system resource usage."""

    timestamp: float = field(default_factory=time.time)

    # CPU
    cpu_percent: float = 0.0          # 0–100
    cpu_count: int = 0

    # RAM
    ram_used_gb: float = 0.0
    ram_total_gb: float = 0.0

    # GPU
    gpu_available: bool = False
    gpu_name: str = "N/A"
    vram_used_gb: float = 0.0
    vram_total_gb: float = 0.0
    gpu_util_percent: float = 0.0     # 0–100
    cuda_available: bool = False

    @property
    def ram_percent(self) -> float:
        if self.ram_total_gb == 0:
            return 0.0
        return (self.ram_used_gb / self.ram_total_gb) * 100.0

    @property
    def vram_percent(self) -> float:
        if self.vram_total_gb == 0:
            return 0.0
        return (self.vram_used_gb / self.vram_total_gb) * 100.0


def probe() -> SystemSnapshot:
    """
    Take a synchronous system snapshot.
    Safe to call from a background worker thread.

    Returns:
        A populated :class:`SystemSnapshot`.
    """
    snap = SystemSnapshot()

    # ── CPU & RAM ─────────────────────────────────────────────────────────
    if _PSUTIL_AVAILABLE:
        try:
            snap.cpu_percent = psutil.cpu_percent(interval=None)
            snap.cpu_count = psutil.cpu_count(logical=True) or 0
            vm = psutil.virtual_memory()
            snap.ram_used_gb = (vm.total - vm.available) / (1024 ** 3)
            snap.ram_total_gb = vm.total / (1024 ** 3)
        except Exception as exc:  # noqa: BLE001
            log.debug("psutil probe failed: %s", exc)

    # ── CUDA detection ────────────────────────────────────────────────────
    try:
        import torch  # noqa: PLC0415
        snap.cuda_available = torch.cuda.is_available()
    except ImportError:
        snap.cuda_available = False

    # ── NVIDIA GPU via pynvml ─────────────────────────────────────────────
    if _PYNVML_AVAILABLE:
        try:
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            snap.gpu_available = True
            snap.gpu_name = pynvml.nvmlDeviceGetName(handle)
            if isinstance(snap.gpu_name, bytes):
                snap.gpu_name = snap.gpu_name.decode()
            mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
            snap.vram_used_gb = mem.used / (1024 ** 3)
            snap.vram_total_gb = mem.total / (1024 ** 3)
            util = pynvml.nvmlDeviceGetUtilizationRates(handle)
            snap.gpu_util_percent = float(util.gpu)
        except Exception as exc:  # noqa: BLE001
            log.debug("pynvml GPU probe failed: %s", exc)

    return snap


def get_available_vram_gb(device_index: int = 0) -> float:
    """
    Return available (free) VRAM on *device_index* in gigabytes.
    Returns 0.0 if pynvml is unavailable or query fails.
    """
    if not _PYNVML_AVAILABLE:
        return 0.0
    try:
        handle = pynvml.nvmlDeviceGetHandleByIndex(device_index)
        mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
        return mem.free / (1024 ** 3)
    except Exception as exc:  # noqa: BLE001
        log.debug("VRAM free query failed: %s", exc)
        return 0.0
