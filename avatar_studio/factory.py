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


def build_provider(settings: Settings):
    """Construct the hosted generation provider for the content channels."""
    if settings.provider == "fal":
        from avatar_studio.providers.fal_provider import FalProvider

        return FalProvider()
    if settings.provider == "fake":
        from avatar_studio.providers.fake import FakeProvider

        return FakeProvider()
    raise ValueError(f"unknown provider {settings.provider!r}")


def build_media_gate(settings: Settings):
    """The single NSFW media gate used by every content channel."""
    from avatar_studio.safety.image_filter import NSFWImageClassifier

    return NSFWImageClassifier(
        settings.nsfw_classifier, settings.nsfw_threshold, settings.device
    )


def build_store(settings: Settings):
    from avatar_studio.store.sqlite_store import SqliteStore

    return SqliteStore(settings.db_url, settings.media_dir)


def build_copywriter(settings: Settings):
    """Persona-voiced copywriter backed by the local LLM brain."""
    from avatar_studio.copy.writer import Copywriter
    from avatar_studio.persona.ollama_backend import OllamaPersona

    llm = OllamaPersona(settings.ollama_url, settings.ollama_model, settings.persona_name)
    return Copywriter(llm)


def build_gen_context(settings: Settings, store=None):
    """Assemble the channel GenContext (provider + gates + store) in one place."""
    from avatar_studio.channels.base import GenContext
    from avatar_studio.safety.text_filter import TextSafety

    return GenContext(
        provider=build_provider(settings),
        media_gate=build_media_gate(settings),
        text_gate=TextSafety(),
        store=store or build_store(settings),
        media_dir=settings.media_dir,
    )
