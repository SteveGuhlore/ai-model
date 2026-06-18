"""Phase 2.2 — persona registry + consent-gated likeness training."""

import pytest

from avatar_studio.personas.registry import ConsentError, PersonaRegistry
from avatar_studio.providers.fake import FakeProvider
from avatar_studio.store.models import Persona, PersonaStatus
from avatar_studio.store.sqlite_store import SqliteStore


def make_registry(tmp_path, provider=None):
    store = SqliteStore(
        db_url=f"sqlite:///{tmp_path}/c.db", media_dir=str(tmp_path / "m")
    )
    return PersonaRegistry(store, provider or FakeProvider()), store


def test_train_requires_consent(tmp_path):
    reg, _ = make_registry(tmp_path)
    p = reg.create(Persona(name="NoConsent", consent_attestation=False))
    with pytest.raises(ConsentError):
        reg.train_likeness(p.id, "https://x/imgs.zip")


def test_train_happy_path_sets_lora_and_ready(tmp_path):
    reg, _ = make_registry(tmp_path)
    p = reg.create(Persona(name="Ava", consent_attestation=True))
    trained = reg.train_likeness(p.id, "https://x/imgs.zip", steps=800)
    assert trained.status is PersonaStatus.READY
    assert trained.likeness_lora_url.endswith(".safetensors")
    assert trained.trigger_word == "ava"


def test_train_marks_failed_on_provider_error(tmp_path):
    class Boom(FakeProvider):
        def train_lora(self, *a, **k):
            raise RuntimeError("provider down")

    reg, store = make_registry(tmp_path, provider=Boom())
    p = reg.create(Persona(name="Ava", consent_attestation=True))
    with pytest.raises(RuntimeError):
        reg.train_likeness(p.id, "https://x/imgs.zip")
    assert store.get_persona(p.id).status is PersonaStatus.FAILED
