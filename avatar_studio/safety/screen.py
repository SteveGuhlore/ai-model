"""Reusable SFW screening facade — the ONE path every channel screens through.

Channels must never call a provider and store the result directly. They go
through ``screen_media`` (images/video) and ``screen_text`` (prompts/copy) so the
load-bearing gates from the existing pipeline apply uniformly to every output
channel. This module adds no new policy of its own beyond two prompt-level
constants; it just guarantees the existing gates are actually invoked and that
both fail closed.
"""

from __future__ import annotations

from avatar_studio.safety.image_filter import NSFWImageClassifier
from avatar_studio.safety.text_filter import SafetyResult, TextSafety

# Standing negative prompt applied to every image generation. Pushes the model
# away from anything explicit; the media gate is still the real enforcement.
SFW_NEGATIVE_PROMPT = (
    "nsfw, nude, nudity, naked, topless, explicit, sexual, suggestive, "
    "genitalia, exposed breasts, see-through clothing, lingerie removal, "
    "fetish, pornographic, erotic, underage, child"
)

# Appended to every channel prompt to keep subjects clothed and platform-safe.
CLOTHING_POLICY_SUFFIX = (
    "fully clothed in tasteful attire, modest, SFW, advertising-appropriate, "
    "natural pose, professional lighting"
)


def screen_text(text: str, gate: TextSafety) -> SafetyResult:
    """Screen a prompt or generated copy string. Returns the gate's SafetyResult."""
    return gate.check(text or "")


def screen_media(media_path: str, gate: NSFWImageClassifier) -> bool:
    """Screen a generated image/video file. Returns True only if SFW.

    Fails closed: any exception from the gate is treated as unsafe (block).
    """
    try:
        return bool(gate.is_sfw(media_path))
    except Exception:
        return False
