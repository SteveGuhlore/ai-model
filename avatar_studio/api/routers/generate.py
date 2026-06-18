"""Content generation + review endpoints.

POST /generate runs a channel batch; every output is already gate-screened by the
channel layer before it is stored. Content lands in review_status=pending — the
review endpoints are the human-in-the-loop approval seam (nothing publishes
without an explicit approve).
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from avatar_studio.api.deps import gen_context, registry, store
from avatar_studio.channels.base import Brief, PromptBlocked
from avatar_studio.channels.lifestyle import LifestyleGenerator
from avatar_studio.store.models import Content, ReviewStatus

router = APIRouter(tags=["content"])

# Only channels implemented so far. Others raise 400 until their phase lands.
_CHANNELS = {"lifestyle": LifestyleGenerator}


class GenerateIn(BaseModel):
    persona_id: str
    channel: str = "lifestyle"
    prompt: str
    placements: list[str] = ["ig_square"]
    count: int = 1
    seed: int | None = None


def _content_out(c: Content) -> dict:
    return {
        "id": c.id,
        "persona_id": c.persona_id,
        "channel": c.channel,
        "kind": c.kind,
        "safety_status": c.safety_status.value,
        "review_status": c.review_status.value,
        "media_url": f"/media/{c.media_path}" if c.media_path else None,
        "aspect_ratio": c.aspect_ratio,
        "prompt": c.prompt,
    }


@router.post("/generate")
def generate(inp: GenerateIn):
    persona = registry().get(inp.persona_id)
    if persona is None:
        raise HTTPException(404, "persona not found")
    gen_cls = _CHANNELS.get(inp.channel)
    if gen_cls is None:
        raise HTTPException(400, f"channel {inp.channel!r} not available yet")

    gen = gen_cls(gen_context())
    brief = Brief(
        prompt=inp.prompt, placements=inp.placements, count=inp.count, seed=inp.seed
    )
    try:
        produced = gen.generate(persona, brief)
    except PromptBlocked as exc:
        raise HTTPException(422, str(exc))
    return {"created": len(produced), "content": [_content_out(c) for c in produced]}


@router.get("/content")
def list_content(persona_id: str | None = None, review_status: str | None = None):
    rs = ReviewStatus(review_status) if review_status else None
    return [_content_out(c) for c in store().list_content(persona_id, rs)]


class ReviewIn(BaseModel):
    status: str  # approved | rejected


@router.post("/content/{content_id}/review")
def review(content_id: str, inp: ReviewIn):
    if store().get_content(content_id) is None:
        raise HTTPException(404, "content not found")
    try:
        status = ReviewStatus(inp.status)
    except ValueError:
        raise HTTPException(422, "invalid review status")
    if status is ReviewStatus.PENDING:
        raise HTTPException(422, "cannot set review back to pending")
    store().set_review_status(content_id, status)
    return {"id": content_id, "review_status": status.value}
