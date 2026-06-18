"""fal.ai model ids in ONE place.

Every fal model id used by the codebase lives here so there is a single point to
confirm/update against official docs. Do not inline model-id string literals
elsewhere. Items marked VERIFY are in reviews/research-fal-meta-tiktok.md's
"VERIFY BEFORE BUILD" list and should be re-checked on the live /api page before
the owning phase ships to production.

Python client: ``pip install fal-client``; auth via the ``FAL_KEY`` env var
(never hard-coded, never shipped to a browser).
"""

from __future__ import annotations

# Image generation (FLUX.1 [dev]). Uses image_size presets, not aspect_ratio.
FLUX_TEXT_TO_IMAGE = "fal-ai/flux/dev"

# LoRA inference: pass a trained LoRA weights url alongside the prompt.
FLUX_LORA_INFERENCE = "fal-ai/flux-lora"

# Likeness LoRA training. VERIFY vs fal-ai/flux-lora-portrait-trainer for better
# identity fidelity on people before committing in production.
FLUX_LORA_TRAINING = "fal-ai/flux-lora-fast-training"

# Image-to-video for guaranteed 9:16 vertical. The Standard tier ignores
# aspect_ratio (ratio follows the source image); Pro/Master tiers accept
# aspect_ratio in {16:9, 9:16, 1:1}. VERIFY exact id before production.
IMAGE_TO_VIDEO_9_16 = "fal-ai/kling-video/v2.1/pro/image-to-video"

# Text-to-speech (zero-shot voice clone). VERIFY input schema before use.
TTS = "fal-ai/f5-tts"
