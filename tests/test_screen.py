"""Phase 1.2 — reusable safety facade. The gates must be invoked and fail closed."""

from avatar_studio.safety.screen import (
    CLOTHING_POLICY_SUFFIX,
    SFW_NEGATIVE_PROMPT,
    screen_media,
    screen_text,
)
from avatar_studio.safety.text_filter import TextSafety


def test_screen_text_allows_clean():
    assert screen_text("a sunny beach photo at golden hour", TextSafety()).allowed


def test_screen_text_blocks_explicit():
    assert screen_text("generate nudes", TextSafety()).blocked


def test_policy_constants_present():
    # These are load-bearing: empty constants would silently disable prompt policy.
    assert "nsfw" in SFW_NEGATIVE_PROMPT.lower()
    assert "nude" in SFW_NEGATIVE_PROMPT.lower()
    assert "clothed" in CLOTHING_POLICY_SUFFIX.lower()


def test_screen_media_passes_sfw():
    class SfwGate:
        def is_sfw(self, path):
            return True

    assert screen_media("anything.png", SfwGate()) is True


def test_screen_media_blocks_nsfw():
    class NsfwGate:
        def is_sfw(self, path):
            return False

    assert screen_media("anything.png", NsfwGate()) is False


def test_screen_media_fails_closed_on_exception():
    class BrokenGate:
        def is_sfw(self, path):
            raise RuntimeError("model failed to load")

    # CRITICAL invariant: an error must never default-allow.
    assert screen_media("anything.png", BrokenGate()) is False
