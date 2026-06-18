"""Per-channel content generators (lifestyle, product ads, tiktok, meta ads).

All channels screen every output through the shared safety plumbing in base.py.
"""

from avatar_studio.channels.base import Brief, GenContext
from avatar_studio.channels.lifestyle import LifestyleGenerator

__all__ = ["Brief", "GenContext", "LifestyleGenerator"]
