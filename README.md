# 🇮🇳 Bharat TTS Studio

<div align="center">
  <h3>An Offline-First Desktop Studio for Indian Text-to-Speech Synthesis</h3>
</div>

<br/>

**Bharat TTS Studio** is an advanced, offline-first desktop application designed for seamlessly generating, comparing, and analyzing Indian Text-to-Speech (TTS) models. Built with a responsive **PySide6** user interface and heavily optimized **PyTorch** adapters, it provides researchers and creators with a unified platform to evaluate both lightweight local neural networks and high-fidelity cloud models side by side.

---

## Key Features

- **Multi-Model Comparison:** Generate and evaluate audio from multiple TTS architectures simultaneously using the same normalized input prompt.
- **Robust Text Normalization:** A 15-stage preprocessing pipeline designed explicitly to handle the complex phonetics and scripts of Indian languages.
- **Hardware-Aware Memory Management:** Dynamically loads model weights into VRAM only during inference and purges them immediately after, strictly adhering to an intelligent memory budget to prevent out-of-memory (OOM) crashes on consumer GPUs (e.g., 8GB RTX 4060).
- **Integrated Workspace:** Built-in audio playback, waveform/spectrogram visualization, and an interactive history browser to manage your synthesized outputs.
- **Cloud Fallbacks:** Guarantees zero-downtime synthesis by transparently falling back to Microsoft Edge TTS and Google Translate TTS when local hardware limits are reached.

---

## Architectural Deep Dive: Supported Models

The studio employs a hybrid approach, supporting highly compressed local VITS models, expressive generative LLMs, and zero-VRAM cloud endpoints.

### 1. Suno Bark (Small)
* **Architecture:** Text-to-Semantic-Token Transformer → Semantic-to-Audio Decoder.
* **Analysis:** Bark operates unlike traditional phoneme-based TTS. It acts as an autoregressive Language Model that predicts discrete audio tokens. This gives it unparalleled expressiveness—allowing it to natively generate non-verbal cues (laughs, sighs) and highly emotional prosody.
* **Uniqueness:** Driven purely by `voice_presets` rather than raw speaker embeddings, making it capable of astonishingly human-like rhythms.
* **Footprint:** Requires ~3.5GB VRAM. Enforced `float16` precision in this repository ensures it runs safely on mid-range GPUs.
* **Languages:** Hindi, Bengali, Tamil, Telugu, English.

### 2. Silero TTS (`v3_indic`)
* **Architecture:** VITS (Variational Inference with adversarial learning for end-to-end Text-to-Speech).
* **Analysis:** An exceptionally streamlined, end-to-end architecture that maps text directly to waveforms. It bypasses traditional separate vocoder stages (like HiFiGAN), resulting in blazing fast inference times.
* **Uniqueness:** Incredibly compact (~60 MB checkpoint) while offering 48 kHz high-fidelity output. Thanks to dynamic transliteration (via `aksharamukha`), it acts as a single unified checkpoint for 10 distinct Indian languages.
* **Languages:** Hindi, Marathi, Bengali, Gujarati, Punjabi, Telugu, Malayalam, Kannada, Tamil, Odia.

### 3. Meta MMS-TTS (Massively Multilingual Speech)
* **Architecture:** VITS-based discrete models.
* **Analysis:** Built by Meta, this project released independent, highly-optimized VITS checkpoints for over 1,000 languages. 
* **Uniqueness:** While Bark uses a single massive model and Silero clusters regional languages into one checkpoint, MMS provides dedicated, laser-focused checkpoints for each specific language. This guarantees maximum phonetic accuracy for regional dialects at a microscopic VRAM cost (~150MB per language).
* **Languages:** 14 distinct Indian languages.

### 4. Microsoft Edge TTS
* **Architecture:** Cloud-hosted Neural TTS (Azure Cognitive Services).
* **Analysis:** Leverages Microsoft's massive server-side infrastructure to deliver broadcast-quality, natural-sounding voices.
* **Uniqueness:** Implemented as an API adapter, it consumes **zero local VRAM** and generates audio almost instantly. It serves as the ultimate fallback for low-end hardware.

### 5. Google Translate TTS (gTTS)
* **Architecture:** Cloud-hosted concatenative/neural fallback.
* **Uniqueness:** Ubiquitous, lightning-fast, and completely unmetered. While it lacks the emotional range of Bark or Azure, it provides guaranteed synthesis for almost any regional language when all local models fail or lack coverage.

---

## Hardware Acceleration: CPU vs. CUDA

Bharat TTS Studio is explicitly designed to respect your hardware constraints. Within the Settings tab, users can toggle the inference engine between **CPU** and **CUDA** (NVIDIA GPU).

### Why the Toggle Exists
1. **CUDA (Recommended):** Leverages PyTorch's GPU acceleration. Synthesizing audio on a model like Suno Bark takes seconds on an RTX 4060, compared to minutes on a CPU. 
2. **CPU Fallback:** Generative LLM-based TTS models (like Bark) consume significant memory. If you are rendering 3D graphics or running a local LLM simultaneously, your VRAM may be exhausted. Toggling to CPU allows you to offload the TTS generation to your system RAM, preventing CUDA out-of-memory crashes at the cost of slower generation speed.

*Note: The application employs a strict `SystemMonitor` that probes your GPU before loading any local model. If the required footprint exceeds your available VRAM, the app intercepts the crash and safely notifies you via the Event Bus.*

---

## Setup & Installation

### 1. Environment Setup
Create and activate a Python 3.10+ virtual environment:
```bash
python -m venv .venv
.venv\Scripts\activate
```

### 2. PyTorch (CUDA 12.1)
For NVIDIA GPU acceleration (highly recommended), install the specific CUDA-compiled PyTorch wheels:
```bash
pip install torch==2.3.1+cu121 torchaudio==2.3.1+cu121 --index-url https://download.pytorch.org/whl/cu121
```

### 3. Dependencies
Install the required application libraries (PySide6, Transformers, etc.):
```bash
pip install -r requirements.txt
```

### 4. Launch the Studio
```bash
python app/main.py
```

---

## Repository Structure

- `app/models/adapters/`: The core implementations integrating Hugging Face, PyTorch Hub, and Cloud APIs.
- `app/engine/`: Orchestration logic for safely allocating VRAM and coordinating concurrent synthesis.
- `app/preprocessing/`: Custom 15-stage phonetic and script normalization.
- `app/gui/`: The PySide6 frontend, strictly decoupled from inference via Qt Signals (Event Bus).
- `config/`: YAML-driven model catalogs and application settings.

## License
The Bharat TTS Studio application code is provided under the MIT License. Please refer to the individual model cards (Meta, Suno, Silero) for their respective weights and usage licenses.
