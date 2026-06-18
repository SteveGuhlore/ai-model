"""In-memory fake provider for tests and offline dev.

Deterministic, no network, no GPU. Lets tests control the returned bytes and
plant an ``nsfw_flag`` (or PNG-magic-tagged "unsafe" bytes) to exercise the
safety gates without any real model.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from avatar_studio.providers.base import ImageResult, LoraResult, VideoResult

# Minimal valid PNG header so PIL can open generated test bytes if needed.
_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


@dataclass
class FakeProvider:
    """Records calls; returns canned bytes. ``nsfw_image_indexes`` flags which
    images in a batch should report ``nsfw_flag=True``."""

    nsfw_image_indexes: set[int] = field(default_factory=set)
    video_nsfw: bool = False
    calls: list[tuple] = field(default_factory=list)

    def generate_image(
        self,
        prompt,
        *,
        negative,
        aspect_ratio,
        lora_url=None,
        seed=None,
        n=1,
    ):
        self.calls.append(("generate_image", prompt, negative, aspect_ratio, lora_url, seed, n))
        out = []
        for i in range(n):
            out.append(
                ImageResult(
                    data=_PNG_MAGIC + f"img-{i}".encode(),
                    seed=(seed or 0) + i,
                    nsfw_flag=i in self.nsfw_image_indexes,
                )
            )
        return out

    def image_to_video(self, image, *, prompt, aspect_ratio, duration_s=5):
        self.calls.append(("image_to_video", prompt, aspect_ratio, duration_s))
        return VideoResult(data=b"FAKEVIDEO", nsfw_flag=self.video_nsfw)

    def train_lora(self, images_zip_url, *, trigger_word, steps=1000):
        self.calls.append(("train_lora", images_zip_url, trigger_word, steps))
        return LoraResult(weights_url=f"https://fake/lora/{trigger_word}.safetensors")
