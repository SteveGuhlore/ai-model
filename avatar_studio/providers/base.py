"""Generation provider contract.

The content channels depend only on this structural protocol, never on a
concrete provider, so fal.ai can be swapped for Replicate/etc. and tests can run
against an in-memory fake with no network and no GPU.

All provider methods return raw bytes / urls; safety screening happens in the
channel layer (avatar_studio.safety.screen) before anything is stored. A
provider is a data plane only — it must not be trusted to be safe on its own.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class ImageResult:
    """One generated image plus provider-reported safety hints.

    ``nsfw_flag`` mirrors a provider signal (e.g. Flux ``has_nsfw_concepts``). It
    is an *extra* pre-gate hint, never a replacement for the media gate.
    """

    data: bytes
    seed: int | None = None
    nsfw_flag: bool = False
    width: int | None = None
    height: int | None = None


@dataclass
class VideoResult:
    data: bytes
    nsfw_flag: bool = False


@dataclass
class LoraResult:
    weights_url: str
    config: dict = field(default_factory=dict)


class GenerationProvider(Protocol):
    def generate_image(
        self,
        prompt: str,
        *,
        negative: str,
        aspect_ratio: str,
        lora_url: str | None = None,
        seed: int | None = None,
        n: int = 1,
    ) -> list[ImageResult]: ...

    def image_to_video(
        self,
        image: bytes,
        *,
        prompt: str,
        aspect_ratio: str,
        duration_s: int = 5,
    ) -> VideoResult: ...

    def train_lora(
        self,
        images_zip_url: str,
        *,
        trigger_word: str,
        steps: int = 1000,
    ) -> LoraResult: ...
