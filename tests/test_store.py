"""Phase 2.1 — SQLite store CRUD + content invariants."""

import pytest

from avatar_studio.store.models import (
    Content,
    Persona,
    Product,
    ReviewStatus,
    SafetyStatus,
)
from avatar_studio.store.sqlite_store import SqliteStore


def make_store(tmp_path):
    return SqliteStore(
        db_url=f"sqlite:///{tmp_path}/creator.db", media_dir=str(tmp_path / "media")
    )


def test_persona_round_trip(tmp_path):
    s = make_store(tmp_path)
    p = s.create_persona(Persona(name="Ava", brand_voice="playful", consent_attestation=True))
    got = s.get_persona(p.id)
    assert got.name == "Ava"
    assert got.consent_attestation is True
    assert [x.id for x in s.list_personas()] == [p.id]


def test_content_requires_safety_status(tmp_path):
    s = make_store(tmp_path)
    c = s.create_content(
        Content(
            persona_id="persona_x",
            channel="lifestyle",
            kind="image",
            safety_status=SafetyStatus.PASSED,
        )
    )
    assert c.review_status is ReviewStatus.PENDING  # never auto-approved
    assert s.get_content(c.id).safety_status is SafetyStatus.PASSED


def test_content_rejects_bad_safety_status(tmp_path):
    s = make_store(tmp_path)
    bad = Content(persona_id="p", channel="lifestyle", kind="image", safety_status="passed")
    with pytest.raises(ValueError):
        s.create_content(bad)


def test_content_review_filter_and_update(tmp_path):
    s = make_store(tmp_path)
    c = s.create_content(
        Content(persona_id="p1", channel="tiktok", kind="video",
                safety_status=SafetyStatus.PASSED)
    )
    assert len(s.list_content(review_status=ReviewStatus.PENDING)) == 1
    s.set_review_status(c.id, ReviewStatus.APPROVED)
    assert len(s.list_content(review_status=ReviewStatus.PENDING)) == 0
    assert len(s.list_content(review_status=ReviewStatus.APPROVED)) == 1


def test_product_round_trip(tmp_path):
    s = make_store(tmp_path)
    p = s.create_product(Product(name="Lace set", category="intimates"))
    assert s.get_product(p.id).category == "intimates"


def test_list_products(tmp_path):
    s = make_store(tmp_path)
    assert s.list_products() == []
    s.create_product(Product(name="A"))
    s.create_product(Product(name="B"))
    assert {p.name for p in s.list_products()} == {"A", "B"}
