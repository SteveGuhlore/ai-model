"""Channel generator contract + shared safe-image plumbing.

The single most important rule in this layer: **a generated image becomes a
stored Content row only after it has passed the media gate**. Every channel
reuses ``screen_and_store_image`` so no channel can accidentally introduce a path
around the gate. The provider's ``nsfw_flag`` is an additional early drop, never
a substitute for the gate.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Protocol

from avatar_studio.providers.base import ImageResult
from avatar_studio.safety.screen import (
    CLOTHING_POLICY_SUFFIX,
    SFW_NEGATIVE_PROMPT,
    screen_media,
    screen_text,
)
from avatar_studio.store.models import Content, Persona, SafetyStatus
from avatar_studio.store.sqlite_store import SqliteStore


@dataclass
class Brief:
    prompt: str
    placements: list[str] = field(default_factory=lambda: ["ig_square"])
    count: int = 1
    seed: int | None = None


@dataclass
class GenContext:
    """Everything a channel needs, injected (testable with fakes)."""

    provider: object
    media_gate: object  # has .is_sfw(path) -> bool
    text_gate: object  # TextSafety
    store: SqliteStore
    media_dir: str


class ChannelGenerator(Protocol):
    def generate(self, persona: Persona, brief: Brief) -> list[Content]: ...


class PromptBlocked(RuntimeError):
    pass


def build_prompt(persona: Persona, brief_prompt: str, ctx: GenContext) -> str:
    """Compose persona trigger + brief + standing clothing policy, and text-gate it."""
    parts = [p for p in (persona.trigger_word, brief_prompt, CLOTHING_POLICY_SUFFIX) if p]
    prompt = ", ".join(parts)
    if screen_text(prompt, ctx.text_gate).blocked:
        raise PromptBlocked("prompt blocked by SFW text gate")
    return prompt


def screen_and_store_image(
    img: ImageResult,
    *,
    persona: Persona,
    channel: str,
    prompt: str,
    aspect_ratio: str,
    ctx: GenContext,
    product_id: str | None = None,
) -> Content | None:
    """Write bytes, run the media gate, and store ONLY if SFW.

    Returns the stored Content, or None if the image was dropped (provider nsfw
    flag, or gate block). Dropped media is deleted from disk.
    """
    # Early drop on the provider's own NSFW signal — cheap, before disk/gate.
    if img.nsfw_flag:
        return None

    from avatar_studio.store.models import new_id

    persona_dir = os.path.join(ctx.media_dir, persona.id)
    os.makedirs(persona_dir, exist_ok=True)
    content_id = new_id("content")
    path = os.path.join(persona_dir, f"{content_id}.png")
    with open(path, "wb") as f:
        f.write(img.data)

    if not screen_media(path, ctx.media_gate):  # fail-closed inside screen_media
        os.remove(path)
        return None

    content = Content(
        id=content_id,
        persona_id=persona.id,
        channel=channel,
        kind="image",
        safety_status=SafetyStatus.PASSED,
        prompt=prompt,
        media_path=os.path.relpath(path, ctx.media_dir),
        aspect_ratio=aspect_ratio,
        product_id=product_id,
    )
    return ctx.store.create_content(content)


__all__ = [
    "Brief",
    "GenContext",
    "ChannelGenerator",
    "PromptBlocked",
    "build_prompt",
    "screen_and_store_image",
    "SFW_NEGATIVE_PROMPT",
]
