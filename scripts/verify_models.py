"""
scripts/verify_models.py
========================
Standalone script to download, load, and test inference on MMS-TTS models.
Usage:
    $env:PYTHONUTF8=1; python scripts/verify_models.py --model mms-tts-hin --text "नमस्ते"
"""

import sys
from pathlib import Path
import argparse
import soundfile as sf

# Ensure we can import 'app'
sys.path.insert(0, str(Path(__file__).parents[1]))

# Import models package to trigger adapter registration
import app.models  # noqa: F401
from app.models.model_manager import ModelManager
from app.core.logger import get_logger

log = get_logger("verify_models")

def main():
    parser = argparse.ArgumentParser(description="Verify TTS models offline.")
    parser.add_argument("--model", type=str, required=True, help="Model ID from catalog (e.g. mms-tts-hin)")
    parser.add_argument("--text", type=str, required=True, help="Text to synthesize")
    parser.add_argument("--device", type=str, default="cuda", choices=["cpu", "cuda"], help="Device to run inference on")
    parser.add_argument("--out", type=str, default="test_output.wav", help="Output audio file path")
    
    args = parser.parse_args()
    
    try:
        manager = ModelManager()
        log.info(f"Available models: {[m['id'] for m in manager.get_available_models()]}")
        
        # Load and generate
        log.info(f"Generating audio using {args.model} on {args.device}...")
        waveform, sr = manager.generate_audio(
            model_id=args.model,
            text=args.text,
            device=args.device
        )
        
        # Save to file
        sf.write(args.out, waveform, sr)
        log.info(f"Success! Audio saved to {args.out} (SR: {sr})")
        
        # Ensure it unloads cleanly
        manager.unload_current_model()
        
    except Exception as exc:
        log.error(f"Verification failed: {exc}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
