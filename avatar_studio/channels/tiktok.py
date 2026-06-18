"""TikTok vertical (9:16) video generator.

Pipeline: generate a 9:16 still (LoRA likeness) -> image-to-video -> the media
gate samples the video's frames and blocks if any is NSFW -> attach a gated
hook + caption. Trend awareness is a pluggable TrendSource (manual feed now,
scraper later) and is never a hard dependency.
"""

from __future__ import annotations

from typing import Protocol

from avatar_studio.channels.base import (
    SFW_NEGATIVE_PROMPT,
    Brief,
    GenContext,
    build_prompt,
    screen_and_store_video,
)
from avatar_studio.copy.writer import Copywriter
from avatar_studio.store.models import Content, Persona

CHANNEL = "tiktok"
ASPECT = "9:16"


class TrendSource(Protocol):
    def get_hint(self) -> str: ...


class TikTokGenerator:
    def __init__(
        self,
        ctx: GenContext,
        copywriter: Copywriter,
        trend_source: TrendSource | None = None,
        duration_s: int = 5,
    ) -> None:
        self.ctx = ctx
        self.copy = copywriter
        self.trend = trend_source
        self.duration_s = duration_s

    def generate(self, persona: Persona, brief: Brief) -> list[Content]:
        hint = self.trend.get_hint() if self.trend else ""
        topic = brief.prompt + (f", trending: {hint}" if hint else "")
        prompt = build_prompt(persona, topic, self.ctx)

        hook = self.copy.write(persona, "hook", topic)
        caption = self.copy.write(persona, "caption", topic)
        copy_text = "\n".join(
            d.text for d in (hook, caption) if not d.blocked and d.text
        )

        stored: list[Content] = []
        for _ in range(brief.count):
            imgs = self.ctx.provider.generate_image(
                prompt,
                negative=SFW_NEGATIVE_PROMPT,
                aspect_ratio=ASPECT,
                lora_url=persona.likeness_lora_url or None,
                seed=brief.seed,
                n=1,
            )
            if not imgs:  # provider returned nothing for this still
                continue
            still = imgs[0]
            if still.nsfw_flag:  # cheap early drop; video gate is the real check
                continue
            video = self.ctx.provider.image_to_video(
                still.data, prompt=prompt, aspect_ratio=ASPECT, duration_s=self.duration_s
            )
            content = screen_and_store_video(
                video.data,
                persona=persona,
                channel=CHANNEL,
                prompt=prompt,
                aspect_ratio=ASPECT,
                ctx=self.ctx,
                copy_text=copy_text,
                nsfw_flag=video.nsfw_flag,
            )
            if content is not None:
                stored.append(content)
        return stored
