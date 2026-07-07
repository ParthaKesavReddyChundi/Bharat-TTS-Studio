"""
tests/unit/core/test_audio_manager.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[3]))

import numpy as np
from unittest.mock import patch
from app.core.audio_manager import AudioManager

def test_audio_manager_play():
    wav = np.zeros(100, dtype=np.float32)
    with patch("app.core.audio_manager.sd.play") as mock_play:
        AudioManager.play(wav, 16000)
        mock_play.assert_called_once()
        assert np.array_equal(mock_play.call_args[0][0], wav)

def test_audio_manager_stop():
    with patch("app.core.audio_manager.sd.stop") as mock_stop:
        AudioManager.stop()
        mock_stop.assert_called_once()

def test_audio_manager_save(tmp_path):
    wav = np.zeros(100, dtype=np.float32)
    out_path = tmp_path / "test.wav"
    
    with patch("app.core.audio_manager.sf.write") as mock_write:
        success = AudioManager.save(str(out_path), wav, 16000)
        assert success is True
        mock_write.assert_called_once()
