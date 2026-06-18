"""Pluggable generation providers (image / video / voice / LoRA training).

The channel layer depends only on ``GenerationProvider`` (see base.py). fal.ai is
the default production implementation; ``FakeProvider`` backs the test suite.
"""

from avatar_studio.providers.base import (
    GenerationProvider,
    ImageResult,
    LoraResult,
    VideoResult,
)

__all__ = [
    "GenerationProvider",
    "ImageResult",
    "VideoResult",
    "LoraResult",
]
