"""
app/models/model_manager.py
===========================
High-level orchestrator for TTS models.
Reads config/models_catalog.yaml, queries the model registry, instantiates
adapters, and manages memory (ensuring only one active model is loaded).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from app.core.logger import get_logger
from app.models.base_adapter import TTSModelAdapter
from app.models.model_registry import get_adapter_class

log = get_logger(__name__)


class ModelManager:
    """
    Manages the lifecycle of TTS models defined in the catalog.
    """

    def __init__(self, catalog_path: str | Path | None = None) -> None:
        """
        Initialize the ModelManager and load the catalog.

        Args:
            catalog_path: Path to models_catalog.yaml.
        """
        if catalog_path is None:
            # Default to <project_root>/config/models_catalog.yaml
            self.catalog_path = Path(__file__).parents[2] / "config" / "models_catalog.yaml"
        else:
            self.catalog_path = Path(catalog_path)

        self.models_config: dict[str, Any] = {}
        self.active_adapter: TTSModelAdapter | None = None
        
        self._load_catalog()

    def _load_catalog(self) -> None:
        """Load the YAML catalog into memory."""
        if not self.catalog_path.exists():
            log.warning("Catalog file not found at %s. No models available.", self.catalog_path)
            return

        try:
            with open(self.catalog_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                
            if not data or "models" not in data:
                log.warning("Catalog file %s is empty or missing 'models' key.", self.catalog_path)
                return

            for model_cfg in data["models"]:
                model_id = model_cfg.get("id")
                if not model_id:
                    log.error("A model in the catalog is missing an 'id'. Skipping.")
                    continue
                self.models_config[model_id] = model_cfg
                
            log.info("Loaded %d models from catalog.", len(self.models_config))
        except Exception as exc:  # noqa: BLE001
            log.error("Failed to load models catalog: %s", exc, exc_info=True)

    def get_available_models(self) -> list[dict[str, Any]]:
        """
        Return a list of all model configurations from the catalog.
        Useful for populating GUI dropdowns.
        """
        return list(self.models_config.values())

    def get_models_for_language(self, lang: str) -> list[dict[str, Any]]:
        """Return all models that support the given language code."""
        return [
            cfg for cfg in self.models_config.values()
            if lang in cfg.get("languages", [])
        ]

    def load_model(self, model_id: str, device: str = "cpu") -> TTSModelAdapter:
        """
        Load a model by ID. If another model is active, it will be unloaded first.
        Before loading, checks available VRAM against the model's `required_vram_gb`
        and the global `memory_budget_vram_gb` from settings. Raises OutOfMemoryError
        (caught by the worker and surfaced as an EventBus toast) if budget is exceeded.

        Args:
            model_id: The ID of the model to load.
            device: 'cpu' or 'cuda'.

        Returns:
            The instantiated and loaded TTSModelAdapter.

        Raises:
            ValueError: If the model_id is not in the catalog.
            OutOfMemoryError: If there is insufficient VRAM for the requested model.
            RuntimeError: If model loading fails.
        """
        if model_id not in self.models_config:
            raise ValueError(f"Model ID '{model_id}' not found in catalog.")

        # If it's already the active model and loaded, just return it
        if self.active_adapter and self.active_adapter.model_id == model_id:
            if self.active_adapter.is_loaded and self.active_adapter.device == device:
                log.debug("Model %s is already loaded on %s.", model_id, device)
                return self.active_adapter

        config = self.models_config[model_id]
        required_vram_gb: float = config.get("required_vram_gb", 0.0)

        # --- VRAM budget gate (only meaningful when loading onto CUDA) ---
        if required_vram_gb > 0.0:
            from app.core import system_monitor  # noqa: PLC0415
            from app.core.config_manager import ConfigManager  # noqa: PLC0415
            from app.core.exceptions import OutOfMemoryError as OOMError  # noqa: PLC0415
            
            if device == "cuda":
                # Read budget from settings; default 6 GB if key is missing
                try:
                    budget_gb: float = ConfigManager().get("hardware.memory_budget_vram_gb", 6.0)
                except Exception:  # noqa: BLE001
                    budget_gb = 6.0
    
                available_gb = system_monitor.get_available_vram_gb()
                
                if available_gb > 0.0:
                    # Unload current model first to reclaim VRAM, then re-check
                    if self.active_adapter:
                        log.info(
                            "Pre-emptively unloading '%s' to free VRAM before loading '%s'.",
                            self.active_adapter.model_id, model_id
                        )
                        self.unload_current_model()
                        available_gb = system_monitor.get_available_vram_gb()
        
                    log.info(
                        "VRAM check for '%s': requires=%.1f GB, available=%.1f GB, budget=%.1f GB",
                        model_id, required_vram_gb, available_gb, budget_gb
                    )
        
                    if available_gb < required_vram_gb or required_vram_gb > budget_gb:
                        err = OOMError(
                            model_id=model_id,
                            required_gb=required_vram_gb,
                            available_gb=available_gb,
                        )
                        log.error("VRAM budget exceeded for model '%s': %s", model_id, err)
                        # Surface via EventBus so the GUI shows a toast (not a crash dialog)
                        try:
                            from app.event_bus import EventBus  # noqa: PLC0415
                            EventBus.instance().toast_requested.emit(str(err), "ERROR")
                        except Exception:  # noqa: BLE001
                            pass
                        raise err
                else:
                    log.warning("Could not verify VRAM (system_monitor returned 0.0). Bypassing manager guard.")
                    
            elif device == "cpu":
                try:
                    import psutil  # noqa: PLC0415
                    available_ram = psutil.virtual_memory().available / (1024**3)
                    
                    if available_ram < required_vram_gb:
                        err = OOMError(
                            model_id=model_id,
                            required_gb=required_vram_gb,
                            available_gb=available_ram,
                        )
                        log.error("RAM budget exceeded for model '%s': %s", model_id, err)
                        try:
                            from app.event_bus import EventBus  # noqa: PLC0415
                            EventBus.instance().toast_requested.emit(str(err), "ERROR")
                        except Exception:  # noqa: BLE001
                            pass
                        raise err
                except OOMError:
                    raise
                except Exception as e:
                    log.warning("Could not verify CPU RAM in manager: %s. Bypassing guard.", e)
            
        # Unload current model to free memory (if not already done above)
        self.unload_current_model()

        # Instantiate new adapter
        adapter_type = config.get("adapter_type")
        if not adapter_type:
            raise ValueError(f"Model '{model_id}' is missing 'adapter_type' in catalog.")

        adapter_cls = get_adapter_class(adapter_type)
        log.info("Instantiating adapter %s for model %s", adapter_type, model_id)

        try:
            adapter = adapter_cls(model_id, config)
            # Load weights
            success = adapter.load(device=device)
            if not success:
                from app.core.exceptions import ModelLoadError  # noqa: PLC0415
                raise ModelLoadError(model_id, "Adapter returned False during load.")
        except Exception as e:
            if type(e).__name__ == "ModelLoadError" or type(e).__name__ == "OutOfMemoryError":
                raise
            log.error("Native model load failure", exc_info=True)
            from app.core.exceptions import ModelLoadError  # noqa: PLC0415
            err = ModelLoadError(model_id, f"Load failed: {str(e)}")
            try:
                from app.event_bus import EventBus  # noqa: PLC0415
                EventBus.instance().toast_requested.emit(str(err), "ERROR")
            except Exception:  # noqa: BLE001
                pass
            raise err

        self.active_adapter = adapter
        log.info("Successfully loaded model %s on %s.", model_id, device)
        return adapter

    def unload_current_model(self) -> None:
        """Unload the currently active model (if any) and clear VRAM aggressively."""
        if self.active_adapter:
            log.info("Unloading current model: %s", self.active_adapter.model_id)
            self.active_adapter.unload()
            self.active_adapter = None
        
        # Aggressive memory cleanup
        import gc
        import torch
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    def generate_audio(self, model_id: str, text: str, lang: str = "hi", speaker_id: str | None = None, device: str = "cpu") -> tuple[Any, int]:
        """
        Convenience method to load (if necessary) and generate audio in one step.
        """
        adapter = self.load_model(model_id, device=device)
        return adapter.generate_audio(text, lang=lang, speaker_id=speaker_id)
