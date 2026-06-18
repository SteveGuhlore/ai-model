"""Phase 2.3 + 3.3 — persona + generate API, end-to-end with the fake provider.

Forces the app to use the fake provider and a temp DB via env before import, and
injects an allow-all media gate so no ML stack is needed.
"""

import importlib

import pytest


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("AVATAR_PROVIDER", "fake")
    monkeypatch.setenv("AVATAR_DB_URL", f"sqlite:///{tmp_path}/api.db")
    monkeypatch.setenv("AVATAR_MEDIA_DIR", str(tmp_path / "media"))

    # Fresh import so module-level Settings pick up the env.
    import avatar_studio.api.deps as deps
    import avatar_studio.api.routers.personas as personas
    import avatar_studio.api.routers.generate as generate
    import avatar_studio.api.app as app_mod

    for m in (deps, personas, generate, app_mod):
        importlib.reload(m)

    # Inject an allow-all media gate so generation doesn't need transformers.
    class GateAllow:
        def is_sfw(self, path):
            return True

    import avatar_studio.factory as factory

    monkeypatch.setattr(factory, "build_media_gate", lambda s: GateAllow())

    # Stub the copywriter so API tests don't reach the Ollama backend.
    from avatar_studio.copy.writer import Copywriter

    class FixedLLM:
        def reply(self, message, history):
            return "clean upbeat copy"

    monkeypatch.setattr(factory, "build_copywriter", lambda s: Copywriter(FixedLLM()))

    from fastapi.testclient import TestClient

    return TestClient(app_mod.app)


def test_health(client):
    assert client.get("/health").json()["status"] == "ok"


def test_persona_lifecycle_and_consent_gate(client):
    r = client.post("/personas", json={"name": "Ava", "consent_attestation": False})
    pid = r.json()["id"]
    # training without consent is refused
    t = client.post(f"/personas/{pid}/train", json={"images_zip_url": "https://x/i.zip"})
    assert t.status_code == 403


def test_generate_flow_and_review(client):
    pid = client.post(
        "/personas", json={"name": "Ava", "trigger_word": "ava", "consent_attestation": True}
    ).json()["id"]
    client.post(f"/personas/{pid}/train", json={"images_zip_url": "https://x/i.zip"})

    g = client.post(
        "/generate",
        json={"persona_id": pid, "channel": "lifestyle", "prompt": "on the beach",
              "placements": ["tiktok"], "count": 2},
    )
    assert g.status_code == 200
    body = g.json()
    assert body["created"] == 2
    cid = body["content"][0]["id"]
    assert body["content"][0]["review_status"] == "pending"

    # content listing + human approval
    pending = client.get("/content", params={"review_status": "pending"}).json()
    assert len(pending) == 2
    ap = client.post(f"/content/{cid}/review", json={"status": "approved"})
    assert ap.json()["review_status"] == "approved"
    assert len(client.get("/content", params={"review_status": "pending"}).json()) == 1


def test_generate_blocks_explicit_prompt(client):
    pid = client.post(
        "/personas", json={"name": "Ava", "consent_attestation": True}
    ).json()["id"]
    g = client.post(
        "/generate", json={"persona_id": pid, "prompt": "nude beach photoshoot"}
    )
    assert g.status_code == 422


def _ready_persona(client):
    pid = client.post(
        "/personas", json={"name": "Ava", "trigger_word": "ava", "consent_attestation": True}
    ).json()["id"]
    client.post(f"/personas/{pid}/train", json={"images_zip_url": "https://x/i.zip"})
    return pid


def test_tiktok_channel_generates_video(client):
    pid = _ready_persona(client)
    g = client.post(
        "/generate",
        json={"persona_id": pid, "channel": "tiktok", "prompt": "beach trend", "count": 2},
    )
    assert g.status_code == 200
    assert g.json()["created"] == 2
    assert all(c["kind"] == "video" for c in g.json()["content"])


def test_product_ad_endpoint(client):
    pid = _ready_persona(client)
    prod = client.post("/products", json={"name": "Lace set", "category": "intimates"}).json()["id"]
    g = client.post(
        "/generate/product-ad",
        json={"persona_id": pid, "product_id": prod, "prompt": "studio",
              "placements": ["ig_portrait"], "count": 2},
    )
    assert g.status_code == 200
    assert g.json()["created"] == 2


def test_meta_ad_endpoint(client):
    pid = _ready_persona(client)
    g = client.post(
        "/generate/meta-ad",
        json={"persona_id": pid, "prompt": "lifestyle",
              "placements": ["ig_square", "ig_portrait"], "count": 1, "copy_variants": 2},
    )
    assert g.status_code == 200
    body = g.json()
    assert len(body["creatives"]) == 2
    assert len(body["primary_texts"]) == 2
    assert body["variant_count"] == 4


def test_count_over_limit_rejected(client):
    pid = _ready_persona(client)
    g = client.post(
        "/generate",
        json={"persona_id": pid, "channel": "lifestyle", "prompt": "x", "count": 9999},
    )
    assert g.status_code == 422  # bounded to prevent unbounded paid batches


def test_unknown_placement_is_422_not_500(client):
    pid = _ready_persona(client)
    g = client.post(
        "/generate",
        json={"persona_id": pid, "prompt": "x", "placements": ["billboard"]},
    )
    assert g.status_code == 422


def test_invalid_review_status_is_422(client):
    assert client.get("/content", params={"review_status": "bogus"}).status_code == 422


def test_unknown_channel_rejected(client):
    pid = client.post(
        "/personas", json={"name": "Ava", "consent_attestation": True}
    ).json()["id"]
    g = client.post(
        "/generate", json={"persona_id": pid, "channel": "carrier_pigeon", "prompt": "hi"}
    )
    assert g.status_code == 400
