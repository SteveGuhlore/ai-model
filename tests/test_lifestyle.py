"""Phase 3.1 — lifestyle generator. CRITICAL: nothing is stored without the gate."""

import os

from avatar_studio.channels.base import Brief, GenContext, PromptBlocked
from avatar_studio.channels.lifestyle import LifestyleGenerator
from avatar_studio.providers.fake import FakeProvider
from avatar_studio.safety.text_filter import TextSafety
from avatar_studio.store.models import Persona, SafetyStatus
from avatar_studio.store.sqlite_store import SqliteStore
import pytest


class GateAllow:
    def is_sfw(self, path):
        return True


class GateBlock:
    def is_sfw(self, path):
        return False


class GateExplode:
    def is_sfw(self, path):
        raise RuntimeError("classifier crashed")


def make_ctx(tmp_path, provider, gate):
    store = SqliteStore(
        db_url=f"sqlite:///{tmp_path}/c.db", media_dir=str(tmp_path / "media")
    )
    return GenContext(
        provider=provider,
        media_gate=gate,
        text_gate=TextSafety(),
        store=store,
        media_dir=str(tmp_path / "media"),
    ), store


def persona():
    return Persona(name="Ava", trigger_word="ava", consent_attestation=True,
                   likeness_lora_url="https://lora")


def test_generates_and_stores_passing_images(tmp_path):
    ctx, store = make_ctx(tmp_path, FakeProvider(), GateAllow())
    gen = LifestyleGenerator(ctx)
    out = gen.generate(persona(), Brief(prompt="on the beach", placements=["tiktok"], count=3))
    assert len(out) == 3
    assert all(c.safety_status is SafetyStatus.PASSED for c in out)
    assert all(c.aspect_ratio == "9:16" for c in out)
    # files exist on disk
    for c in out:
        assert os.path.exists(os.path.join(ctx.media_dir, c.media_path))


def test_prompt_includes_clothing_policy_and_negative(tmp_path):
    prov = FakeProvider()
    ctx, _ = make_ctx(tmp_path, prov, GateAllow())
    LifestyleGenerator(ctx).generate(persona(), Brief(prompt="beach", placements=["ig_square"]))
    call = prov.calls[0]
    _, sent_prompt, negative, aspect, lora, seed, n = call
    assert "clothed" in sent_prompt.lower()
    assert "ava" in sent_prompt.lower()
    assert "nsfw" in negative.lower()
    assert lora == "https://lora"


def test_nsfw_flagged_images_are_dropped(tmp_path):
    # provider pre-flags image index 0 as nsfw -> must not be stored
    ctx, store = make_ctx(tmp_path, FakeProvider(nsfw_image_indexes={0}), GateAllow())
    out = LifestyleGenerator(ctx).generate(
        persona(), Brief(prompt="beach", placements=["tiktok"], count=2)
    )
    assert len(out) == 1
    assert len(store.list_content()) == 1


def test_gate_block_stores_nothing_and_cleans_disk(tmp_path):
    ctx, store = make_ctx(tmp_path, FakeProvider(), GateBlock())
    out = LifestyleGenerator(ctx).generate(
        persona(), Brief(prompt="beach", placements=["tiktok"], count=3)
    )
    assert out == []
    assert store.list_content() == []
    # no orphan files left on disk
    leftover = []
    for _root, _dirs, files in os.walk(ctx.media_dir):
        leftover.extend(files)
    assert leftover == []


def test_gate_exception_fails_closed(tmp_path):
    # CRITICAL: a crashing classifier must block, never store.
    ctx, store = make_ctx(tmp_path, FakeProvider(), GateExplode())
    out = LifestyleGenerator(ctx).generate(
        persona(), Brief(prompt="beach", placements=["tiktok"], count=2)
    )
    assert out == []
    assert store.list_content() == []


def test_explicit_brief_is_blocked_before_generation(tmp_path):
    prov = FakeProvider()
    ctx, _ = make_ctx(tmp_path, prov, GateAllow())
    with pytest.raises(PromptBlocked):
        LifestyleGenerator(ctx).generate(persona(), Brief(prompt="nude photoshoot"))
    assert prov.calls == []  # provider never called on a blocked prompt
