"""
tests/unit/models/test_model_manager.py
=======================================
Tests for ModelManager and ModelRegistry logic.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[3]))

import pytest
import numpy as np

# Ensure adapters are registered
import app.models  # noqa: F401
from app.models.model_manager import ModelManager
from app.models.base_adapter import TTSModelAdapter
from app.models.model_registry import register_adapter, get_adapter_class


# Dummy adapter for testing
class DummyAdapter(TTSModelAdapter):
    def load(self, device="cpu"):
        self.device = device
        self.is_loaded = True
        return True
        
    def unload(self):
        self.is_loaded = False
        
    def generate_audio(self, text, lang="hi", speaker_id=None):
        return np.array([0.1, 0.2, 0.3], dtype=np.float32), 16000


@pytest.fixture
def mock_catalog(tmp_path):
    """Creates a temporary catalog for testing."""
    import yaml
    catalog_path = tmp_path / "models_catalog.yaml"
    catalog_data = {
        "models": [
            {
                "id": "dummy-1",
                "adapter_type": "dummy",
                "languages": ["hi", "en"]
            },
            {
                "id": "dummy-2",
                "adapter_type": "dummy",
                "languages": ["te"]
            }
        ]
    }
    with open(catalog_path, "w") as f:
        yaml.dump(catalog_data, f)
    return catalog_path


def test_registry():
    register_adapter("dummy", DummyAdapter)
    cls = get_adapter_class("dummy")
    assert cls is DummyAdapter
    
    with pytest.raises(ValueError):
        get_adapter_class("nonexistent")


def test_model_manager_loading(mock_catalog):
    register_adapter("dummy", DummyAdapter)
    manager = ModelManager(catalog_path=mock_catalog)
    
    models = manager.get_available_models()
    assert len(models) == 2
    
    hi_models = manager.get_models_for_language("hi")
    assert len(hi_models) == 1
    assert hi_models[0]["id"] == "dummy-1"
    
    # Test load
    adapter = manager.load_model("dummy-1", device="cpu")
    assert adapter.is_loaded
    assert adapter.device == "cpu"
    assert manager.active_adapter is adapter
    
    # Test generate
    wav, sr = manager.generate_audio("dummy-1", "test text")
    assert len(wav) == 3
    assert sr == 16000
    
    # Test unload
    manager.unload_current_model()
    assert manager.active_adapter is None
    assert not adapter.is_loaded
