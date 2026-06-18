"""Adult-mode policy preflight endpoints.

These endpoints do not generate or deliver adult media. They exist so the CRM and
future adult channels can fail closed before any paid provider call happens.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from avatar_studio.api.deps import registry, settings
from avatar_studio.policy.adult import AdultContentPolicy, AdultPolicyInput

router = APIRouter(prefix="/adult", tags=["adult-policy"])


class AdultPolicyCheckIn(BaseModel):
    prompt: str = Field(min_length=1, max_length=2000)
    platform: str = Field(default="fanvue", min_length=1, max_length=64)
    persona_id: str | None = None
    consent_attestation: bool = False
    subject_age_verified: bool = False
    ai_disclosure_acknowledged: bool = False


@router.post("/policy-check")
def adult_policy_check(inp: AdultPolicyCheckIn):
    consent = inp.consent_attestation
    persona_id = inp.persona_id
    if persona_id:
        persona = registry().get(persona_id)
        if persona is None:
            raise HTTPException(404, "persona not found")
        consent = consent or persona.consent_attestation

    policy = AdultContentPolicy.from_settings(settings())
    result = policy.evaluate(
        AdultPolicyInput(
            prompt=inp.prompt,
            platform=inp.platform,
            consent_attestation=consent,
            subject_age_verified=inp.subject_age_verified,
            ai_disclosure_acknowledged=inp.ai_disclosure_acknowledged,
        )
    )
    return {
        "allowed": result.allowed,
        "decision": result.decision.value,
        "platform": result.platform,
        "reasons": result.reasons,
        "requires_human_review": result.requires_human_review,
    }
