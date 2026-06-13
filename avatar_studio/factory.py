"""Construct the production backends from Settings.

Heavy/IO backend imports happen *inside* the functions, so importing this
module stays light (no torch, no fastapi). Both the API and the Gradio UI use
these builders so wiring lives in exactly one place.
"""

from __future__ import annotations

from avatar_studio.config import Settings


def build_pipeline(settings: Settings):
    from avatar_studio.persona.ollama_backend import OllamaPersona
    from avatar_studio.pipeline import AvatarPipeline
    from avatar_studio.safety.image_filter import NSFWImageClassifier
    from avatar_studio.safety.text_filter import TextSafety
    from avatar_studio.talkinghead.renderer import SadTalkerRenderer
    from avatar_studio.voice.tts import VoiceCloneTTS

    return AvatarPipeline(
        persona=OllamaPersona(settings.ollama_url, settings.ollama_model, settings.persona_name),
        tts=VoiceCloneTTS(
            settings.tts_model,
            settings.voice_sample,
            settings.tts_language,
            settings.device,
        ),
        head=SadTalkerRenderer(settings.sadtalker_dir, settings.device),
        face_image=settings.face_image,
        text_safety=TextSafety(),
        media_safety=NSFWImageClassifier(
            settings.nsfw_classifier, settings.nsfw_threshold, settings.device
        ),
        work_dir=settings.work_dir,
    )


def build_face_generator(settings: Settings):
    from avatar_studio.face.generate import FaceGenerator

    return FaceGenerator(settings.sdxl_base, settings.lora_path, settings.device)
