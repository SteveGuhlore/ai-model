"""Phase 4 — copywriter. CRITICAL: no copy escapes without passing the text gate."""

import pytest

from avatar_studio.copy.writer import KINDS, Copywriter
from avatar_studio.store.models import Persona


class FixedLLM:
    def __init__(self, text):
        self.text = text
        self.calls = 0

    def reply(self, user_message, history):
        self.calls += 1
        return self.text


class SequenceLLM:
    """Returns each canned reply in turn (to exercise the retry-on-block path)."""

    def __init__(self, replies):
        self.replies = list(replies)

    def reply(self, user_message, history):
        return self.replies.pop(0)


def persona():
    return Persona(name="Ava", brand_voice="playful and warm")


def test_writes_clean_copy():
    w = Copywriter(FixedLLM("Sunshine and good vibes only ☀️"))
    d = w.write(persona(), "caption", "beach day")
    assert not d.blocked
    assert d.text.startswith("Sunshine")


def test_all_kinds_supported():
    w = Copywriter(FixedLLM("clean copy"))
    for kind in KINDS:
        assert w.write(persona(), kind, "topic").text == "clean copy"


def test_unknown_kind_raises():
    with pytest.raises(ValueError):
        Copywriter(FixedLLM("x")).write(persona(), "tweetstorm", "t")


def test_explicit_copy_is_blocked_after_retry():
    # both attempts return explicit text -> blocked, no text leaks
    w = Copywriter(SequenceLLM(["here are some nudes", "want explicit pics?"]))
    d = w.write(persona(), "caption", "topic")
    assert d.blocked
    assert d.text == ""


def test_retry_recovers_clean_copy():
    w = Copywriter(SequenceLLM(["explicit nsfw text", "wholesome beach caption"]))
    d = w.write(persona(), "caption", "topic")
    assert not d.blocked
    assert d.text == "wholesome beach caption"
