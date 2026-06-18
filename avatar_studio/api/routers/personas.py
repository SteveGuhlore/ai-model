"""Persona management endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from avatar_studio.api.deps import job_runner, registry
from avatar_studio.personas.registry import ConsentError
from avatar_studio.store.models import Persona

router = APIRouter(prefix="/personas", tags=["personas"])


class PersonaIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    brand_voice: str = Field(default="", max_length=1000)
    trigger_word: str = Field(default="", max_length=60)
    voice_ref: str = Field(default="", max_length=500)
    consent_attestation: bool = False


class TrainIn(BaseModel):
    images_zip_url: str = Field(min_length=1, max_length=2000)
    steps: int = Field(default=1000, ge=1, le=5000)


def _out(p: Persona) -> dict:
    return {
        "id": p.id,
        "name": p.name,
        "brand_voice": p.brand_voice,
        "trigger_word": p.trigger_word,
        "status": p.status.value,
        "consent_attestation": p.consent_attestation,
        "likeness_lora_url": p.likeness_lora_url,
    }


@router.post("")
def create_persona(inp: PersonaIn):
    p = registry().create(Persona(**inp.model_dump()))
    return _out(p)


@router.get("")
def list_personas():
    return [_out(p) for p in registry().list()]


@router.get("/{persona_id}")
def get_persona(persona_id: str):
    p = registry().get(persona_id)
    if p is None:
        raise HTTPException(404, "persona not found")
    return _out(p)


@router.post("/{persona_id}/train", status_code=202)
def train_persona(persona_id: str, inp: TrainIn):
    # Validate synchronously (fast) so 404/403 surface immediately; the actual
    # 20-40 min training runs as a background job the client polls via /jobs/{id}.
    persona = registry().get(persona_id)
    if persona is None:
        raise HTTPException(404, "persona not found")
    if not persona.consent_attestation:
        raise HTTPException(403, "likeness training requires a consent attestation")

    def work():
        try:
            p = registry().train_likeness(persona_id, inp.images_zip_url, steps=inp.steps)
        except ConsentError as exc:  # re-checked defensively inside train_likeness
            raise RuntimeError(str(exc))
        return {"persona_id": p.id, "status": p.status.value,
                "likeness_lora_url": p.likeness_lora_url}

    job = job_runner().submit("train_likeness", work, persona_id=persona_id)
    return {"job_id": job.id, "status": job.status.value}
