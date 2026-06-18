"""Per-channel content generators (lifestyle, product ads, tiktok, meta ads).

All channels screen every output through the shared safety plumbing in base.py.
"""

from avatar_studio.channels.base import Brief, GenContext
from avatar_studio.channels.lifestyle import LifestyleGenerator
from avatar_studio.channels.meta_ads import MetaAdAssembler, MetaAdSetDraft
from avatar_studio.channels.product_ad import ProductAdGenerator
from avatar_studio.channels.tiktok import TikTokGenerator

__all__ = [
    "Brief",
    "GenContext",
    "LifestyleGenerator",
    "ProductAdGenerator",
    "TikTokGenerator",
    "MetaAdAssembler",
    "MetaAdSetDraft",
]
