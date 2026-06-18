"""Meta (Facebook/Instagram) ad-creative assembler.

Produces a structured ad-set *draft*: N gate-passed image creatives across Meta
aspect ratios x gated copy variants (primary text + headline). It does NOT upload
anything — live ad creation is Phase 9 (control-plane, human-gated, requires Meta
App Review + Business Verification). Lingerie/apparel creatives stay clothed and
SFW; they still pass through a human review queue before any submission.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from avatar_studio.channels.base import (
    SFW_NEGATIVE_PROMPT,
    Brief,
    GenContext,
    build_prompt,
    screen_and_store_image,
)
from avatar_studio.channels.sizing import spec_for
from avatar_studio.copy.writer import Copywriter
from avatar_studio.store.models import Content, Persona, Product

CHANNEL = "meta_ad"
DEFAULT_PLACEMENTS = ["ig_square", "ig_portrait"]


@dataclass
class MetaAdSetDraft:
    persona_id: str
    creatives: list[Content] = field(default_factory=list)  # gate-passed images
    primary_texts: list[str] = field(default_factory=list)
    headlines: list[str] = field(default_factory=list)
    product_id: str | None = None

    @property
    def variant_count(self) -> int:
        return len(self.creatives) * max(1, len(self.primary_texts))


class MetaAdAssembler:
    def __init__(self, ctx: GenContext, copywriter: Copywriter) -> None:
        self.ctx = ctx
        self.copy = copywriter

    def assemble(
        self,
        persona: Persona,
        brief: Brief,
        *,
        product: Product | None = None,
        copy_variants: int = 2,
    ) -> MetaAdSetDraft:
        topic = brief.prompt
        if product is not None:
            topic = f"modeling {product.name}" + (f". {brief.prompt}" if brief.prompt else "")
        prompt = build_prompt(persona, topic, self.ctx)

        placements = brief.placements or DEFAULT_PLACEMENTS
        draft = MetaAdSetDraft(
            persona_id=persona.id, product_id=(product.id if product else None)
        )

        for placement in placements:
            spec = spec_for(placement)
            images = self.ctx.provider.generate_image(
                prompt,
                negative=SFW_NEGATIVE_PROMPT,
                aspect_ratio=spec.aspect_ratio,
                lora_url=persona.likeness_lora_url or None,
                seed=brief.seed,
                n=brief.count,
            )
            for img in images:
                content = screen_and_store_image(
                    img,
                    persona=persona,
                    channel=CHANNEL,
                    prompt=prompt,
                    aspect_ratio=spec.aspect_ratio,
                    ctx=self.ctx,
                    product_id=(product.id if product else None),
                )
                if content is not None:
                    draft.creatives.append(content)

        for _ in range(copy_variants):
            pt = self.copy.write(persona, "fb_primary_text", topic)
            hl = self.copy.write(persona, "fb_headline", topic)
            if not pt.blocked and pt.text:
                draft.primary_texts.append(pt.text)
            if not hl.blocked and hl.text:
                draft.headlines.append(hl.text)
        return draft
