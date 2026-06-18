"""Product / dropship ad generator.

The persona models a brand's product (apparel/intimates/etc.) in SFW, clothed,
advertising-appropriate shots, with persona-voiced ad copy. Intimates are handled
as clothed product modeling — the clothing policy + media gate apply exactly as
for every other channel; nothing explicit is ever produced.
"""

from __future__ import annotations

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

CHANNEL = "product_ad"


class ProductAdGenerator:
    def __init__(self, ctx: GenContext, copywriter: Copywriter) -> None:
        self.ctx = ctx
        self.copy = copywriter

    def generate(self, persona: Persona, product: Product, brief: Brief) -> list[Content]:
        product_brief = (
            f"modeling {product.name}"
            + (f" ({product.category})" if product.category else "")
            + (f", {product.description}" if product.description else "")
            + (f". {brief.prompt}" if brief.prompt else "")
        )
        prompt = build_prompt(persona, product_brief, self.ctx)

        # One gated ad copy for the batch (regenerated/dropped inside the writer).
        draft = self.copy.write(persona, "fb_primary_text", product_brief)
        copy_text = "" if draft.blocked else draft.text

        stored: list[Content] = []
        for placement in brief.placements:
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
                    product_id=product.id,
                    copy_text=copy_text,
                )
                if content is not None:
                    stored.append(content)
        return stored
