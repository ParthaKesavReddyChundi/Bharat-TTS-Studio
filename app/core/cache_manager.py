"""
app/core/cache_manager.py
==========================
Content-addressed LRU cache for generated audio.

Cache key: SHA-256 of (normalized_text + model_id + speaker + emotion +
           str(rate) + str(pitch)) — independent of volume (applied post-cache).

Cache layout on disk:
    cache/
      <sha256_hex>/
        audio.wav          ← the audio file
        meta.yaml          ← GenerationMetadata (latency, RTF, etc.)

Phase 1 status: STUB — API defined, implementation deferred to Phase 4.
"""

from __future__ import annotations

from pathlib import Path

from app.core.logger import get_logger

log = get_logger(__name__)


class CacheManager:
    """
    Stub for Phase 1.  Full implementation in Phase 4.

    The public interface is defined here so other modules can import and call it
    without caring which phase actually fills in the body.
    """

    def __init__(self, cache_dir: Path | str = Path("cache"), max_size_mb: int = 500) -> None:
        self._cache_dir = Path(cache_dir)
        self._max_size_mb = max_size_mb
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        log.debug("CacheManager initialised (stub). Cache dir: %s", self._cache_dir)

    def has(self, cache_key: str) -> bool:
        """Return True if *cache_key* exists in cache."""
        # Phase 4: check (cache_dir / cache_key / audio.wav).exists()
        return False

    def get(self, cache_key: str) -> tuple[Path, dict] | None:
        """Return (audio_path, metadata_dict) for *cache_key*, or None on miss."""
        return None

    def store(self, cache_key: str, audio_path: Path, metadata: dict) -> None:
        """Save *audio_path* and *metadata* under *cache_key*. Evicts LRU if needed."""
        log.debug("CacheManager.store() called (stub — no-op in Phase 1).")

    def clear(self) -> None:
        """Delete all cached entries from disk."""
        log.debug("CacheManager.clear() called (stub — no-op in Phase 1).")

    def size_mb(self) -> float:
        """Return current cache disk usage in megabytes."""
        return 0.0
