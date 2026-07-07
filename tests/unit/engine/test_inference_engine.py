"""
tests/unit/engine/test_inference_engine.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[3]))

import numpy as np
import pytest

from app.engine.inference_engine import InferenceEngine
from app.models.model_manager import ModelManager
from app.models.base_adapter import TTSModelAdapter
from app.models.model_registry import register_adapter

class MockAdapter(TTSModelAdapter):
    def load(self, device="cpu"):
        self.device = device
        self.is_loaded = True
        return True
    
    def unload(self):
        self.is_loaded = False
        
    def generate_audio(self, text, lang="hi", speaker_id=None):
        # Return a dummy sine wave for tests
        return np.sin(np.linspace(0, 440 * 2 * np.pi, 16000)).astype(np.float32), 16000


@pytest.fixture
def mock_catalog(tmp_path):
    import yaml
    catalog_path = tmp_path / "models_catalog.yaml"
    data = {
        "models": [
            {
                "id": "mock-hin",
                "adapter_type": "mock",
                "languages": ["hi"]
            }
        ]
    }
    with open(catalog_path, "w") as f:
        yaml.dump(data, f)
    return catalog_path


def test_inference_engine(mock_catalog):
    register_adapter("mock", MockAdapter)
    manager = ModelManager(catalog_path=mock_catalog)
    engine = InferenceEngine(model_manager=manager)
    
    # 10 ₹ is just an example text
    # The pipeline should normalize it to "दस रुपये" (or similar)
    # The engine should pass it to the MockAdapter
    wav, sr = engine.synthesize("10 ₹", "mock-hin", device="cpu")
    
    assert len(wav) == 16000
    assert sr == 16000
