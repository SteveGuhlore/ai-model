"""Publishing scaffolds (control-plane, human-gated). No autonomous posting."""

from avatar_studio.publishing.base import (
    NotApprovedError,
    PublishResult,
    Publisher,
    require_approved,
)
from avatar_studio.publishing.meta import MetaPublisher
from avatar_studio.publishing.tiktok import TikTokPublisher

__all__ = [
    "Publisher",
    "PublishResult",
    "NotApprovedError",
    "require_approved",
    "TikTokPublisher",
    "MetaPublisher",
]
