# Bharat TTS Studio

Bharat TTS Studio is an offline-first desktop app for comparing Indian text-to-speech models side by side. It uses PySide6 for the UI, PyTorch-based adapters for local models, and cloud-backed fallbacks for comparison and coverage.

## What It Does

- Compare multiple TTS engines with the same input text.
- Normalize Indian text before synthesis with a 15-stage preprocessing pipeline.
- Load local checkpoints only when needed, then unload them to keep memory usage low.
- Play, save, and browse generated WAV files from inside the app.
- Keep the runtime self-contained: the app works after the model checkpoints are downloaded once.

## Model Coverage

The repository currently has two layers of model support:

- Cataloged models exposed by `config/models_catalog.yaml` and the GUI.
- Adapter families implemented in `app/models/adapters/` that are ready for catalog wiring or future expansion.

### Cataloged Models

| Family / IDs | Architecture | Languages in this repo | Training / source notes | Distinctive traits |
| --- | --- | --- | --- | --- |
| Meta MMS-TTS (`mms-tts-hin`, `mms-tts-tam`, `mms-tts-tel`, `mms-tts-mar`, `mms-tts-guj`, `mms-tts-ben`, `mms-tts-kan`, `mms-tts-mal`, `mms-tts-pan`, `mms-tts-urd`, `mms-tts-eng`, `mms-tts-ory`, `mms-tts-asm`, `mms-tts-npi`) | VITS checkpoint per language | hi, ta, te, mr, gu, bn, kn, ml, pa, ur, en, or, as, ne | Public checkpoint cards identify the MMS project and VITS architecture; they do not enumerate the exact per-language corpus mixture in the checkpoint README. | Light local footprint, one model per language, offline inference after download. |
| Silero TTS (`silero-hi`) | Compact VITS-style model via PyTorch Hub | hi, mr | Public details focus on the runtime family; the training corpus is not spelled out in this repository snapshot. | Fast, compact, 48 kHz output, multiple Indic speaker presets. |
| Suno Bark (`bark-small-multi`) | Transformer text-to-semantic-token plus semantic-to-audio decoding | hi, en, ta, te, bn | Public model card describes the Bark family and its inference path, but does not itemize the full pretraining corpus here. | Highly expressive, voice preset driven, can render laughter and other nonverbal audio. |
| Microsoft Edge TTS (`edge-tts-multi`) | Cloud neural voice service | hi, ta, te, mr, bn, ur, gu, kn, ml, pa | Vendor-hosted service; local training data is not exposed because the app calls the online API. | No local GPU/RAM load, broad Indian-language coverage, requires internet. |
| Google Translate TTS (`gtts-multi`) | Cloud speech-synthesis service | hi, ta, te, mr, bn, ur, gu, kn, ml, pa, or, as, ne | Vendor-hosted service; the app uses the online Translate TTS endpoint. | Very light fallback path, no local checkpoint downloads. |

### Implemented Adapter Families

| Family | Status in repo | Architecture | Languages | Training / source notes | Distinctive traits |
| --- | --- | --- | --- | --- | --- |
| SpeechT5 (`speecht5-hi`) | Adapter implemented in code, but not fully wired in the current YAML snapshot | Shared encoder-decoder with SpeechT5 HiFiGAN vocoder | hi | The public model card says the TTS checkpoint is fine-tuned on LibriTTS and uses speaker embeddings from `Matthijs/cmu-arctic-xvectors`. | Open-access neural TTS with a clean speaker-embedding workflow. |
| Indic Parler-TTS (`indic-parler-tts`) | Adapter implemented in code, ready for catalog wiring | Parler-TTS conditional generation with transcript + descriptive caption | Officially supports Assamese, Bengali, Bodo, Dogri, English, Gujarati, Hindi, Kannada, Konkani, Maithili, Malayalam, Manipuri, Marathi, Nepali, Odia, Punjabi, Sanskrit, Santali, Sindhi, Tamil, Telugu, and Urdu | The public model card says the model is a fine-tune of Indic Parler-TTS Pretrained on a 1,806 hour multilingual Indic and English dataset built from GLOBE-annotated, IndicTTS, LIMMITS, and Rasa. | Caption-conditioned speech with controllable style, emotion, and speaker identity. |
| Veena (`maya-research/Veena`) | Adapter implemented in code, ready for catalog wiring | 3B parameter Llama-style autoregressive transformer with SNAC codec | Hindi, English | The public model card says the model was trained on proprietary Hindi and English datasets; the exact corpus is not publicly released. | Speaker tokens, code-mixed output, 24 kHz SNAC decoding, low-latency generation. |

## Module Map

| Module | Responsibility |
| --- | --- |
| `app/main.py` | Application entry point, dependency checks, Qt bootstrap, and startup logging. |
| `app/app_controller.py` | Top-level wiring layer that connects config, history, theme, engine, and the main window. |
| `app/event_bus.py` | Qt signal hub for generation, comparison, model loading, download progress, errors, and toast notifications. |
| `app/core/` | Runtime services: configuration, logging, audio playback, history persistence, cache management, exceptions, and system monitoring. |
| `app/preprocessing/` | The 15-stage text normalization pipeline plus language-specific rule modules. |
| `app/models/` | Adapter registry, downloader, manager, and model-specific runtime adapters. |
| `app/engine/` | High-level orchestration for single-model synthesis and multi-model comparison. |
| `app/inference/` | Compatibility namespace mirroring inference and comparison behavior during the codebase migration. |
| `app/audio/` | Audio analysis, waveform/spectrogram helpers, and post-processing utilities. |
| `app/gui/` | Main window, pages, panels, dialogs, workers, widgets, and theme assets. |
| `app/utils/` | Shared helpers for hashing, file handling, labels, and validation. |
| `scripts/` | Utility scripts for model verification and environment setup. |
| `tests/` | Smoke, unit, and integration tests. |

## Main Features

- Home tab for single-model synthesis.
- Comparison tab for running multiple models against the same prompt.
- History tab for browsing, replaying, opening, and deleting generated audio.
- Settings tab for theme and basic runtime preferences.
- Qt worker threads so the GUI stays responsive while synthesis runs.
- History-backed audio saving in `outputs/history/`.

## Tech Stack

- Python 3.10+
- PySide6 / Qt for the desktop UI
- PyTorch and Hugging Face Transformers for local model loading
- `sounddevice`, `soundfile`, and `librosa` for playback and decoding
- `PyYAML` for config catalogs
- `pyqtgraph` and `matplotlib` for audio visualizations
- `pytest` and `pytest-qt` for tests

## Setup

### 1. Create a virtual environment

```bash
python -m venv .venv
.venv\\Scripts\\activate
```

### 2. Install PyTorch with CUDA support

If you have an NVIDIA GPU, install the CUDA wheel first:

```bash
pip install torch==2.3.1+cu121 torchaudio==2.3.1+cu121 --index-url https://download.pytorch.org/whl/cu121
```

### 3. Install the app dependencies

```bash
pip install -r requirements.txt
```

### 4. Launch the app

```bash
python app/main.py
```

### 5. Optional checks

```bash
python -m pytest
```

## Runtime Notes

- `config/settings.yaml` is created from `config/settings.default.yaml` on first run.
- `config/history.json` is runtime state and should stay out of version control.
- `models/`, `cache/`, `outputs/`, and `logs/` are local runtime folders.
- The app can run on CPU, but local models are much faster with CUDA.

## License

MIT for the application code. Individual model licenses vary and should be checked in the corresponding model cards before redistribution.
