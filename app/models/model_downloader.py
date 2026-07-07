"""
app/models/model_downloader.py
==============================
Handles downloading model weights from HuggingFace Hub to local storage.
Ensures 100% offline inference capability after the initial download.
"""

from __future__ import annotations

import os
from pathlib import Path

from huggingface_hub import snapshot_download

from app.core.logger import get_logger

log = get_logger(__name__)


class ModelDownloader:
    """
    Downloads and caches TTS model checkpoints locally.
    """

    def __init__(self, cache_dir: str | Path | None = None) -> None:
        """
        Initialize the downloader.

        Args:
            cache_dir: Directory to store downloaded models. Defaults to 'models/' in project root.
        """
        if cache_dir is None:
            # Default to <project_root>/models
            self.cache_dir = Path(__file__).parents[2] / "models"
        else:
            self.cache_dir = Path(cache_dir)
            
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        log.debug("ModelDownloader initialized with cache_dir: %s", self.cache_dir)

    def download_model(self, repo_id: str, allow_patterns: list[str] | None = None) -> str:
        """
        Download a model from HuggingFace to the local cache directory.

        Args:
            repo_id: The HuggingFace repository ID (e.g. 'facebook/mms-tts-hin').
            allow_patterns: Optional list of file patterns to download (e.g. ['*.bin', '*.json']).
                            If None, downloads everything.

        Returns:
            str: The absolute path to the downloaded model directory.
        """
        log.info("Requesting download for model: %s", repo_id)
        
        try:
            # We use snapshot_download to get the entire repo (or specific files)
            # local_dir ensures the files are accessible easily without the symlink mess
            # of the default huggingface cache, making true offline use very predictable.
            local_model_path = self.cache_dir / repo_id.replace("/", "_")
            
            # If it already exists and is non-empty, we can skip redownloading if offline
            if local_model_path.exists() and any(local_model_path.iterdir()):
                log.info("Model %s already exists at %s. Skipping download.", repo_id, local_model_path)
                return str(local_model_path)
                
            download_path = snapshot_download(
                repo_id=repo_id,
                local_dir=str(local_model_path),
                local_dir_use_symlinks=False,
                allow_patterns=allow_patterns,
                resume_download=True,
            )
            log.info("Successfully downloaded %s to %s", repo_id, download_path)
            return str(download_path)
            
        except Exception as exc:  # noqa: BLE001
            log.error("Failed to download model %s: %s", repo_id, exc, exc_info=True)
            # If offline and already cached via standard HF cache, we could try to find it,
            # but for this project we require models in the designated local_dir.
            raise RuntimeError(f"Failed to download model {repo_id}: {exc}") from exc
