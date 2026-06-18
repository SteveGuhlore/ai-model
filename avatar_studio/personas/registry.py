"""Persona registry + likeness LoRA training orchestration.

Thin layer over the store + a GenerationProvider. The consent gate is enforced
here: a persona cannot be trained unless it carries an explicit
``consent_attestation`` (the operator's own/consented likeness only).
"""

from __future__ import annotations

from avatar_studio.providers.base import GenerationProvider
from avatar_studio.store.models import Persona, PersonaStatus
from avatar_studio.store.sqlite_store import SqliteStore


class ConsentError(RuntimeError):
    """Raised when training is attempted without a consent attestation."""


class PersonaRegistry:
    def __init__(self, store: SqliteStore, provider: GenerationProvider) -> None:
        self._store = store
        self._provider = provider

    def create(self, persona: Persona) -> Persona:
        return self._store.create_persona(persona)

    def get(self, persona_id: str) -> Persona | None:
        return self._store.get_persona(persona_id)

    def list(self) -> list[Persona]:
        return self._store.list_personas()

    def train_likeness(
        self, persona_id: str, images_zip_url: str, *, steps: int = 1000
    ) -> Persona:
        persona = self._store.get_persona(persona_id)
        if persona is None:
            raise KeyError(persona_id)
        if not persona.consent_attestation:
            raise ConsentError(
                "likeness training requires an explicit consent attestation"
            )
        trigger = persona.trigger_word or persona.name.lower().replace(" ", "")

        persona.status = PersonaStatus.TRAINING
        self._store.update_persona(persona)
        try:
            result = self._provider.train_lora(
                images_zip_url, trigger_word=trigger, steps=steps
            )
        except Exception:
            persona.status = PersonaStatus.FAILED
            self._store.update_persona(persona)
            raise

        persona.likeness_lora_url = result.weights_url
        persona.trigger_word = trigger
        persona.status = PersonaStatus.READY
        return self._store.update_persona(persona)
