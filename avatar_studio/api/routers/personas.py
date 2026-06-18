"""Persona management endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from avatar_studio.api.deps import registry
from avatar_studio.personas.registry import ConsentError
from avatar_studio.store.models import Persona

router = APIRouter(prefix="/personas", tags=["personas"])


class PersonaIn(BaseModel):
    name: str
    brand_voice: str = ""
    trigger_word: str = ""
    voice_ref: str = ""
    consent_attestation: bool = False


class TrainIn(BaseModel):
    images_zip_url: str
    steps: int = 1000


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


@router.post("/{persona_id}/train")
def train_persona(persona_id: str, inp: TrainIn):
    try:
        p = registry().train_likeness(persona_id, inp.images_zip_url, steps=inp.steps)
    except KeyError:
        raise HTTPException(404, "persona not found")
    except ConsentError as exc:
        raise HTTPException(403, str(exc))
    return _out(p)
