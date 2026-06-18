"""Runtime configuration, read from environment variables.

Uses stdlib dataclasses (no pydantic) so the core stays importable without
the app dependencies installed. See .env.example for the full list.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


def _env(key: str, default: str) -> str:
    return os.environ.get(key, default)


def _env_bool(key: str, default: bool) -> bool:
    value = os.environ.get(key)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class Settings:
    # Paths
    work_dir: str = _env("AVATAR_WORK_DIR", "outputs")
    face_image: str = _env("AVATAR_FACE_IMAGE", "assets/face.png")
    models_dir: str = _env("AVATAR_MODELS_DIR", "models")

    # Persona / LLM "brain" (local by default)
    llm_backend: str = _env("AVATAR_LLM_BACKEND", "ollama")
    ollama_url: str = _env("OLLAMA_URL", "http://localhost:11434")
    ollama_model: str = _env("OLLAMA_MODEL", "llama3.1:8b-instruct-q4_K_M")
    persona_name: str = _env("AVATAR_PERSONA_NAME", "Ava")

    # Voice (XTTS-v2 supports cloning from a short reference clip)
    tts_model: str = _env("AVATAR_TTS_MODEL", "tts_models/multilingual/multi-dataset/xtts_v2")
    voice_sample: str = _env("AVATAR_VOICE_SAMPLE", "assets/voice_ref.wav")
    tts_language: str = _env("AVATAR_TTS_LANGUAGE", "en")

    # Face generation (SFW base + your likeness LoRA)
    sdxl_base: str = _env("AVATAR_SDXL_BASE", "stabilityai/stable-diffusion-xl-base-1.0")
    lora_path: str = _env("AVATAR_LORA_PATH", "models/likeness-lora.safetensors")

    # Talking head
    sadtalker_dir: str = _env("SADTALKER_DIR", "third_party/SadTalker")

    # Safety
    nsfw_classifier: str = _env("AVATAR_NSFW_CLASSIFIER", "Falconsai/nsfw_image_detection")
    nsfw_threshold: float = float(_env("AVATAR_NSFW_THRESHOLD", "0.7"))

    # Adult-mode policy spine. Disabled by default; the existing SFW endpoints do
    # not read this flag. Adult endpoints must still enforce consent, age, AI
    # disclosure, platform eligibility, and human review.
    adult_mode_enabled: bool = _env_bool("AVATAR_ADULT_MODE_ENABLED", False)
    adult_allowed_platforms: str = _env("AVATAR_ADULT_ALLOWED_PLATFORMS", "fanvue,telegram")
    adult_require_human_review: bool = _env_bool("AVATAR_ADULT_REQUIRE_HUMAN_REVIEW", True)

    # Hosted generation provider (creator content channels)
    provider: str = _env("AVATAR_PROVIDER", "fal")
    fal_key: str = _env("FAL_KEY", "")

    # Storage (local-first; structured to move to Postgres + object storage later)
    db_url: str = _env("AVATAR_DB_URL", "sqlite:///creator.db")
    media_dir: str = _env("AVATAR_MEDIA_DIR", "media")
    storage_backend: str = _env("AVATAR_STORAGE", "local")

    # Compute
    device: str = _env("AVATAR_DEVICE", "cuda")

    @classmethod
    def from_env(cls) -> "Settings":
        return cls()

