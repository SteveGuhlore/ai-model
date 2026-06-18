"""Content generation + review endpoints.

POST /generate runs a channel batch; every output is already gate-screened by the
channel layer before it is stored. Content lands in review_status=pending — the
review endpoints are the human-in-the-loop approval seam (nothing publishes
without an explicit approve).
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from avatar_studio.api.deps import copywriter, gen_context, registry, store
from avatar_studio.channels.base import Brief, PromptBlocked
from avatar_studio.channels.lifestyle import LifestyleGenerator
from avatar_studio.channels.meta_ads import MetaAdAssembler
from avatar_studio.channels.product_ad import ProductAdGenerator
from avatar_studio.channels.tiktok import TikTokGenerator
from avatar_studio.store.models import Content, Product, ReviewStatus

router = APIRouter(tags=["content"])


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


def _brief(inp) -> Brief:
    return Brief(prompt=inp.prompt, placements=inp.placements, count=inp.count, seed=inp.seed)


def _require_persona(persona_id: str):
    persona = registry().get(persona_id)
    if persona is None:
        raise HTTPException(404, "persona not found")
    return persona


@router.post("/generate")
def generate(inp: GenerateIn):
    """Persona+brief channels: lifestyle (images) and tiktok (video)."""
    persona = _require_persona(inp.persona_id)
    if inp.channel == "lifestyle":
        gen = LifestyleGenerator(gen_context())
    elif inp.channel == "tiktok":
        gen = TikTokGenerator(gen_context(), copywriter())
    else:
        raise HTTPException(400, f"channel {inp.channel!r} not available on this endpoint")
    try:
        produced = gen.generate(persona, _brief(inp))
    except PromptBlocked as exc:
        raise HTTPException(422, str(exc))
    return {"created": len(produced), "content": [_content_out(c) for c in produced]}


class ProductAdIn(GenerateIn):
    product_id: str


@router.post("/generate/product-ad")
def generate_product_ad(inp: ProductAdIn):
    persona = _require_persona(inp.persona_id)
    product = store().get_product(inp.product_id)
    if product is None:
        raise HTTPException(404, "product not found")
    gen = ProductAdGenerator(gen_context(), copywriter())
    try:
        produced = gen.generate(persona, product, _brief(inp))
    except PromptBlocked as exc:
        raise HTTPException(422, str(exc))
    return {"created": len(produced), "content": [_content_out(c) for c in produced]}


class MetaAdIn(GenerateIn):
    product_id: str | None = None
    copy_variants: int = 2


@router.post("/generate/meta-ad")
def generate_meta_ad(inp: MetaAdIn):
    persona = _require_persona(inp.persona_id)
    product = store().get_product(inp.product_id) if inp.product_id else None
    if inp.product_id and product is None:
        raise HTTPException(404, "product not found")
    asm = MetaAdAssembler(gen_context(), copywriter())
    try:
        draft = asm.assemble(persona, _brief(inp), product=product, copy_variants=inp.copy_variants)
    except PromptBlocked as exc:
        raise HTTPException(422, str(exc))
    return {
        "persona_id": draft.persona_id,
        "product_id": draft.product_id,
        "variant_count": draft.variant_count,
        "creatives": [_content_out(c) for c in draft.creatives],
        "primary_texts": draft.primary_texts,
        "headlines": draft.headlines,
    }


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
