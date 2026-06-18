"""Lifestyle / beach photo batch generator.

Generates a batch of on-brand, SFW lifestyle stills for a persona across the
requested placements. Consistency comes from the persona's trigger word + LoRA +
controlled seeds. Every image is screened before it is stored.
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
from avatar_studio.store.models import Content, Persona

CHANNEL = "lifestyle"


class LifestyleGenerator:
    def __init__(self, ctx: GenContext) -> None:
        self.ctx = ctx

    def generate(self, persona: Persona, brief: Brief) -> list[Content]:
        prompt = build_prompt(persona, brief.prompt, self.ctx)
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
                )
                if content is not None:
                    stored.append(content)
        return stored
