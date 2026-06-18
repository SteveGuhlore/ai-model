"""Phases 5-7 — product ads, TikTok video, Meta ad assembly. Gates enforced."""

from avatar_studio.channels.base import Brief, GenContext
from avatar_studio.channels.meta_ads import MetaAdAssembler
from avatar_studio.channels.product_ad import ProductAdGenerator
from avatar_studio.channels.tiktok import TikTokGenerator
from avatar_studio.copy.writer import Copywriter
from avatar_studio.providers.fake import FakeProvider
from avatar_studio.safety.text_filter import TextSafety
from avatar_studio.store.models import Persona, Product
from avatar_studio.store.sqlite_store import SqliteStore


class GateAllow:
    def is_sfw(self, path):
        return True


class GateBlock:
    def is_sfw(self, path):
        return False


class FixedLLM:
    def __init__(self, text="clean upbeat copy"):
        self.text = text

    def reply(self, message, history):
        return self.text


def ctx_for(tmp_path, provider, gate):
    store = SqliteStore(db_url=f"sqlite:///{tmp_path}/c.db", media_dir=str(tmp_path / "m"))
    return GenContext(provider, gate, TextSafety(), store, str(tmp_path / "m")), store


def persona():
    return Persona(name="Ava", trigger_word="ava", consent_attestation=True,
                   likeness_lora_url="https://lora", brand_voice="warm")


# --- Phase 5: product ads ----------------------------------------------
def test_product_ad_generates_with_copy(tmp_path):
    ctx, store = ctx_for(tmp_path, FakeProvider(), GateAllow())
    gen = ProductAdGenerator(ctx, Copywriter(FixedLLM("Shop the look ✨")))
    product = store.create_product(Product(name="Lace set", category="intimates"))
    out = gen.generate(persona(), product, Brief(prompt="studio shot", placements=["ig_portrait"], count=2))
    assert len(out) == 2
    assert all(c.product_id == product.id for c in out)
    assert all(c.copy_text == "Shop the look ✨" for c in out)
    assert all(c.channel == "product_ad" for c in out)


def test_product_ad_blocked_by_media_gate(tmp_path):
    ctx, store = ctx_for(tmp_path, FakeProvider(), GateBlock())
    gen = ProductAdGenerator(ctx, Copywriter(FixedLLM()))
    product = store.create_product(Product(name="Tee"))
    out = gen.generate(persona(), product, Brief(prompt="x", placements=["ig_square"], count=3))
    assert out == []
    assert store.list_content() == []


# --- Phase 6: tiktok video ---------------------------------------------
def test_tiktok_generates_video(tmp_path):
    ctx, store = ctx_for(tmp_path, FakeProvider(), GateAllow())
    gen = TikTokGenerator(ctx, Copywriter(FixedLLM("hook line")))
    out = gen.generate(persona(), Brief(prompt="beach trend", count=2))
    assert len(out) == 2
    assert all(c.kind == "video" for c in out)
    assert all(c.aspect_ratio == "9:16" for c in out)
    assert all(c.copy_text for c in out)


def test_tiktok_video_failing_frame_gate_dropped(tmp_path):
    # video gate blocks -> nothing stored (frame-level NSFW caught)
    ctx, store = ctx_for(tmp_path, FakeProvider(), GateBlock())
    out = TikTokGenerator(ctx, Copywriter(FixedLLM())).generate(
        persona(), Brief(prompt="x", count=2)
    )
    assert out == []
    assert store.list_content() == []


def test_tiktok_nsfw_video_flag_dropped(tmp_path):
    ctx, store = ctx_for(tmp_path, FakeProvider(video_nsfw=True), GateAllow())
    out = TikTokGenerator(ctx, Copywriter(FixedLLM())).generate(
        persona(), Brief(prompt="x", count=2)
    )
    assert out == []


def test_tiktok_uses_trend_source(tmp_path):
    class Trend:
        def get_hint(self):
            return "golden hour sunset transition"

    prov = FakeProvider()
    ctx, _ = ctx_for(tmp_path, prov, GateAllow())
    TikTokGenerator(ctx, Copywriter(FixedLLM()), trend_source=Trend()).generate(
        persona(), Brief(prompt="beach", count=1)
    )
    img_call = next(c for c in prov.calls if c[0] == "generate_image")
    assert "golden hour" in img_call[1]


# --- Phase 7: meta ads -------------------------------------------------
def test_meta_assembles_creatives_and_copy(tmp_path):
    ctx, store = ctx_for(tmp_path, FakeProvider(), GateAllow())
    asm = MetaAdAssembler(ctx, Copywriter(FixedLLM("buy now")))
    draft = asm.assemble(persona(), Brief(prompt="lifestyle", placements=["ig_square", "ig_portrait"], count=1), copy_variants=2)
    assert len(draft.creatives) == 2  # one per placement
    assert len(draft.primary_texts) == 2
    assert len(draft.headlines) == 2
    assert draft.variant_count == 4
    # creatives are stored + gate-passed
    assert len(store.list_content()) == 2


def test_meta_blocked_media_yields_no_creatives(tmp_path):
    ctx, store = ctx_for(tmp_path, FakeProvider(), GateBlock())
    draft = MetaAdAssembler(ctx, Copywriter(FixedLLM())).assemble(
        persona(), Brief(prompt="x", placements=["ig_square"], count=2)
    )
    assert draft.creatives == []
    assert store.list_content() == []
