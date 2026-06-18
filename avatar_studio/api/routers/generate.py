"""Content generation + review endpoints.

POST /generate runs a channel batch; every output is already gate-screened by the
channel layer before it is stored. Content lands in review_status=pending — the
review endpoints are the human-in-the-loop approval seam (nothing publishes
without an explicit approve).
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from avatar_studio.api.deps import copywriter, gen_context, job_runner, registry, store
from avatar_studio.channels.base import Brief
from avatar_studio.channels.lifestyle import LifestyleGenerator
from avatar_studio.channels.meta_ads import MetaAdAssembler
from avatar_studio.channels.product_ad import ProductAdGenerator
from avatar_studio.channels.sizing import spec_for
from avatar_studio.channels.tiktok import TikTokGenerator
from avatar_studio.safety.screen import screen_text
from avatar_studio.safety.text_filter import TextSafety
from avatar_studio.store.models import Content, Product, ReviewStatus

router = APIRouter(tags=["content"])


class GenerateIn(BaseModel):
    # Bounds keep a single request from triggering an unbounded (paid) batch.
    persona_id: str
    channel: str = "lifestyle"
    prompt: str = Field(min_length=1, max_length=2000)
    placements: list[str] = Field(default=["ig_square"], min_length=1, max_length=8)
    count: int = Field(default=1, ge=1, le=12)
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


def _brief(inp) -> Brief:
    return Brief(prompt=inp.prompt, placements=inp.placements, count=inp.count, seed=inp.seed)


def _require_persona(persona_id: str):
    persona = registry().get(persona_id)
    if persona is None:
        raise HTTPException(404, "persona not found")
    return persona


def _validate_request(inp, *, check_placements: bool = True) -> None:
    """Synchronous, provider-free validation so blocked prompts / bad input return
    422 immediately rather than failing an already-accepted background job."""
    if screen_text(inp.prompt, TextSafety()).blocked:
        raise HTTPException(422, "prompt blocked by SFW text gate")
    if check_placements:
        for p in inp.placements:
            try:
                spec_for(p)
            except ValueError as exc:
                raise HTTPException(422, str(exc))


@router.post("/generate", status_code=202)
def generate(inp: GenerateIn):
    """Persona+brief channels: lifestyle (images) and tiktok (video). Async job."""
    persona = _require_persona(inp.persona_id)
    if inp.channel not in ("lifestyle", "tiktok"):
        raise HTTPException(400, f"channel {inp.channel!r} not available on this endpoint")
    _validate_request(inp, check_placements=(inp.channel == "lifestyle"))
    brief = _brief(inp)
    channel = inp.channel

    def work():
        gen = (
            LifestyleGenerator(gen_context())
            if channel == "lifestyle"
            else TikTokGenerator(gen_context(), copywriter())
        )
        produced = gen.generate(persona, brief)
        return {"created": len(produced), "content": [_content_out(c) for c in produced]}

    job = job_runner().submit(f"generate:{channel}", work, persona_id=persona.id)
    return {"job_id": job.id, "status": job.status.value}


class ProductAdIn(GenerateIn):
    product_id: str


@router.post("/generate/product-ad", status_code=202)
def generate_product_ad(inp: ProductAdIn):
    persona = _require_persona(inp.persona_id)
    product = store().get_product(inp.product_id)
    if product is None:
        raise HTTPException(404, "product not found")
    _validate_request(inp, check_placements=True)
    brief = _brief(inp)

    def work():
        gen = ProductAdGenerator(gen_context(), copywriter())
        produced = gen.generate(persona, product, brief)
        return {"created": len(produced), "content": [_content_out(c) for c in produced]}

    job = job_runner().submit("generate:product_ad", work, persona_id=persona.id)
    return {"job_id": job.id, "status": job.status.value}


class MetaAdIn(GenerateIn):
    product_id: str | None = None
    copy_variants: int = Field(default=2, ge=1, le=6)


@router.post("/generate/meta-ad", status_code=202)
def generate_meta_ad(inp: MetaAdIn):
    persona = _require_persona(inp.persona_id)
    product = store().get_product(inp.product_id) if inp.product_id else None
    if inp.product_id and product is None:
        raise HTTPException(404, "product not found")
    _validate_request(inp, check_placements=True)
    brief = _brief(inp)
    copy_variants = inp.copy_variants

    def work():
        asm = MetaAdAssembler(gen_context(), copywriter())
        draft = asm.assemble(persona, brief, product=product, copy_variants=copy_variants)
        return {
            "persona_id": draft.persona_id,
            "product_id": draft.product_id,
            "variant_count": draft.variant_count,
            "creatives": [_content_out(c) for c in draft.creatives],
            "primary_texts": draft.primary_texts,
            "headlines": draft.headlines,
        }

    job = job_runner().submit("generate:meta_ad", work, persona_id=persona.id)
    return {"job_id": job.id, "status": job.status.value}


class ProductIn(BaseModel):
    name: str
    category: str = ""
    description: str = ""
    source_image: str = ""


@router.post("/products")
def create_product(inp: ProductIn):
    p = store().create_product(Product(**inp.model_dump()))
    return {"id": p.id, "name": p.name, "category": p.category}


@router.get("/content")
def list_content(persona_id: str | None = None, review_status: str | None = None):
    try:
        rs = ReviewStatus(review_status) if review_status else None
    except ValueError:
        raise HTTPException(422, "invalid review_status")
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
