import sys
sys.path.insert(0, '.')

print("Testing core module imports...")

from app.core.exceptions import TTSStudioError, ModelNotFoundError, InferenceError
print("  [OK] app.core.exceptions")

from app.core.logger import setup_logging, get_logger
from pathlib import Path
setup_logging(Path("logs"), console_level="DEBUG")
log = get_logger("test")
log.info("Logger works")
print("  [OK] app.core.logger")

from app.core.config_manager import ConfigManager
cfg = ConfigManager()
theme = cfg.get("app.theme")
print(f"  [OK] app.core.config_manager  (theme={theme})")

from app.core.cache_manager import CacheManager
cm = CacheManager()
print("  [OK] app.core.cache_manager")

from app.core.system_monitor import probe
snap = probe()
print(f"  [OK] app.core.system_monitor  (cuda={snap.cuda_available}, gpu={snap.gpu_available})")
if snap.gpu_available:
    print(f"       GPU: {snap.gpu_name}  VRAM: {snap.vram_used_gb:.1f}/{snap.vram_total_gb:.1f} GB")

import yaml
with open("config/models_catalog.yaml", encoding="utf-8") as f:
    cat = yaml.safe_load(f)
enabled = [m["id"] for m in cat["models"] if m.get("available")]
print(f"  [OK] config/models_catalog.yaml  (enabled models: {enabled})")

with open("config/languages_catalog.yaml", encoding="utf-8") as f:
    langs = yaml.safe_load(f)
lang_count = len(langs["languages"])
print(f"  [OK] config/languages_catalog.yaml  ({lang_count} languages)")

# Test event bus (needs PySide6)
from app.event_bus import EventBus
bus = EventBus.instance()
print("  [OK] app.event_bus")

print()
print("=" * 50)
print("All core imports PASSED.")
print("=" * 50)
