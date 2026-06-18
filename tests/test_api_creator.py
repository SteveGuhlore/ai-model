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


def test_unknown_channel_rejected(client):
    pid = client.post(
        "/personas", json={"name": "Ava", "consent_attestation": True}
    ).json()["id"]
    g = client.post(
        "/generate", json={"persona_id": pid, "channel": "tiktok", "prompt": "hi"}
    )
    assert g.status_code == 400
