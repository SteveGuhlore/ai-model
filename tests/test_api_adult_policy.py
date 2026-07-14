import importlib


def make_client(tmp_path, monkeypatch, *, content_modes="sfw,adult"):
    monkeypatch.setenv("AVATAR_PROVIDER", "fake")
    monkeypatch.setenv("AVATAR_DB_URL", f"sqlite:///{tmp_path}/adult.db")
    monkeypatch.setenv("AVATAR_MEDIA_DIR", str(tmp_path / "media"))
    monkeypatch.setenv("AVATAR_CONTENT_MODES", content_modes)
    monkeypatch.setenv("AVATAR_ADULT_ALLOWED_PLATFORMS", "fanvue,telegram")

    import avatar_studio.config as config
    import avatar_studio.api.app as app_mod
    import avatar_studio.api.deps as deps
    import avatar_studio.api.routers.adult as adult
    import avatar_studio.api.routers.generate as generate
    import avatar_studio.api.routers.jobs as jobs
    import avatar_studio.api.routers.personas as personas

    for m in (config, deps, personas, generate, jobs, adult, app_mod):
        importlib.reload(m)

    from fastapi.testclient import TestClient

    return TestClient(app_mod.app)


def test_adult_policy_endpoint_disabled_when_adult_mode_absent(tmp_path, monkeypatch):
    client = make_client(tmp_path, monkeypatch, content_modes="sfw")
    res = client.post(
        "/adult/policy-check",
        json={
            "platform": "fanvue",
            "prompt": "premium studio set",
            "consent_attestation": True,
            "subject_age_verified": True,
            "ai_disclosure_acknowledged": True,
        },
    )
    assert res.status_code == 200
    body = res.json()
    assert body["decision"] == "disabled"
    assert body["allowed"] is False
    assert body["reasons"] == ["adult_content_mode_disabled"]


def test_adult_policy_endpoint_allows_when_enabled(tmp_path, monkeypatch):
    client = make_client(tmp_path, monkeypatch)
    res = client.post(
        "/adult/policy-check",
        json={
            "platform": "telegram",
            "prompt": "premium studio set for verified persona",
            "consent_attestation": True,
            "subject_age_verified": True,
            "ai_disclosure_acknowledged": True,
        },
    )
    assert res.status_code == 200
    assert res.json()["allowed"] is True


def test_adult_policy_endpoint_uses_persona_consent(tmp_path, monkeypatch):
    client = make_client(tmp_path, monkeypatch)
    pid = client.post(
        "/personas",
        json={"name": "Ava", "trigger_word": "ava", "consent_attestation": True},
    ).json()["id"]
    res = client.post(
        "/adult/policy-check",
        json={
            "persona_id": pid,
            "platform": "fanvue",
            "prompt": "premium studio set",
            "subject_age_verified": True,
            "ai_disclosure_acknowledged": True,
        },
    )
    assert res.status_code == 200
    assert res.json()["allowed"] is True


def test_adult_policy_endpoint_blocks_prohibited_terms(tmp_path, monkeypatch):
    client = make_client(tmp_path, monkeypatch)
    res = client.post(
        "/adult/policy-check",
        json={
            "platform": "fanvue",
            "prompt": "underage themed request",
            "consent_attestation": True,
            "subject_age_verified": True,
            "ai_disclosure_acknowledged": True,
        },
    )
    assert res.status_code == 200
    assert res.json()["allowed"] is False
    assert "minor_or_age_ambiguous" in res.json()["reasons"]



