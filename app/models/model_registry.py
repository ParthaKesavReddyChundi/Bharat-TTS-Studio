"""
app/models/model_registry.py
============================
Registers and maps adapter_type strings (from models_catalog.yaml)
to concrete TTSModelAdapter Python classes.
"""

from __future__ import annotations

from typing import Type

from app.core.logger import get_logger
from app.models.base_adapter import TTSModelAdapter

log = get_logger(__name__)

# The global registry mapping adapter types to classes
_ADAPTER_REGISTRY: dict[str, Type[TTSModelAdapter]] = {}


def register_adapter(adapter_type: str, adapter_cls: Type[TTSModelAdapter]) -> None:
    """
    Register a TTS model adapter class under a string type name.

    Args:
        adapter_type: A unique string identifier (e.g. 'mms-tts', 'indic-parida').
        adapter_cls: The subclass of TTSModelAdapter.
    """
    if adapter_type in _ADAPTER_REGISTRY:
        log.warning("Overwriting existing adapter registration for type: %s", adapter_type)
        
    if not issubclass(adapter_cls, TTSModelAdapter):
        raise TypeError(f"Adapter class must inherit from TTSModelAdapter. Got {adapter_cls}")
        
    _ADAPTER_REGISTRY[adapter_type] = adapter_cls
    log.debug("Registered adapter: %s -> %s", adapter_type, adapter_cls.__name__)


def get_adapter_class(adapter_type: str) -> Type[TTSModelAdapter]:
    """
    Retrieve an adapter class by its string type name.

    Args:
        adapter_type: The type string (e.g., 'mms-tts').

    Returns:
        The registered TTSModelAdapter subclass.

    Raises:
        ValueError: If the adapter_type is not registered.
    """
    if adapter_type not in _ADAPTER_REGISTRY:
        raise ValueError(f"Unknown adapter type: '{adapter_type}'. Available: {list(_ADAPTER_REGISTRY.keys())}")
    return _ADAPTER_REGISTRY[adapter_type]
