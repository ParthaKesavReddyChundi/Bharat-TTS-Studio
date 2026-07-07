"""
app/models/__init__.py
======================
Initializes the models module and registers all available adapters.
"""

from app.models.model_registry import register_adapter

# Guaranteed working adapters
from app.models.adapters.mms_tts_adapter import MMSTTSAdapter
from app.models.adapters.silero_adapter import SileroAdapter
from app.models.adapters.bark_adapter import BarkAdapter
from app.models.adapters.edge_tts_adapter import EdgeTTSAdapter
from app.models.adapters.gtts_adapter import GTTSAdapter

# Register adapters — adapter_type in catalog must match the key here
register_adapter("mms-tts", MMSTTSAdapter)
register_adapter("silero", SileroAdapter)
register_adapter("bark", BarkAdapter)
register_adapter("edge_tts", EdgeTTSAdapter)
register_adapter("gtts", GTTSAdapter)
