"""Phase 1.1 — provider contract + fal request-building (no network, no GPU)."""

import pytest

from avatar_studio.providers.fake import FakeProvider
from avatar_studio.providers.fal_provider import FalProvider, _image_size_for


def test_fake_generate_image_batch():
    p = FakeProvider(nsfw_image_indexes={1})
    imgs = p.generate_image(
        "beach", negative="nsfw", aspect_ratio="9:16", lora_url="u", seed=7, n=3
    )
    assert len(imgs) == 3
    assert imgs[0].nsfw_flag is False
    assert imgs[1].nsfw_flag is True
    assert imgs[0].seed == 7


def test_fake_train_lora_returns_url():
    p = FakeProvider()
    res = p.train_lora("https://x/imgs.zip", trigger_word="ava", steps=1000)
    assert res.weights_url.endswith(".safetensors")
    assert ("train_lora", "https://x/imgs.zip", "ava", 1000) in p.calls


def test_image_size_mapping():
    assert _image_size_for("9:16") == "portrait_16_9"
    assert _image_size_for("1:1") == "square_hd"
    assert _image_size_for("4:5") == {"width": 1024, "height": 1280}


def test_image_size_unknown_raises():
    with pytest.raises(ValueError):
        _image_size_for("21:9")


class _FakeFalClient:
    """Stands in for the fal_client module; records the run() call."""

    def __init__(self, result):
        self.result = result
        self.last = None

    def run(self, model, arguments):
        self.last = (model, arguments)
        return self.result

    def upload(self, data, content_type):
        return "https://fal/upload/x.png"


def test_fal_generate_builds_request_and_validates(monkeypatch):
    client = _FakeFalClient(
        {
            "images": [{"url": "https://fal/img.png", "width": 1024, "height": 1024}],
            "seed": 42,
            "has_nsfw_concepts": [False],
        }
    )
    prov = FalProvider(client=client)
    # avoid real download
    monkeypatch.setattr(FalProvider, "_download", staticmethod(lambda url: b"PNGBYTES"))
    imgs = prov.generate_image("beach", negative="n", aspect_ratio="9:16", seed=42, n=1)
    model, args = client.last
    assert model == "fal-ai/flux/dev"
    assert args["image_size"] == "portrait_16_9"
    assert args["seed"] == 42
    assert imgs[0].data == b"PNGBYTES"


def test_fal_generate_with_lora_switches_model(monkeypatch):
    client = _FakeFalClient(
        {"images": [{"url": "https://fal/img.png"}], "has_nsfw_concepts": [False]}
    )
    prov = FalProvider(client=client)
    monkeypatch.setattr(FalProvider, "_download", staticmethod(lambda url: b"X"))
    prov.generate_image("p", negative="n", aspect_ratio="1:1", lora_url="https://lora")
    model, args = client.last
    assert model == "fal-ai/flux-lora"
    assert args["loras"][0]["path"] == "https://lora"


def test_fal_per_image_seed_not_shared(monkeypatch):
    client = _FakeFalClient(
        {
            "images": [
                {"url": "https://fal/a.png", "seed": 11},
                {"url": "https://fal/b.png", "seed": 22},
            ],
            "seed": 11,
            "has_nsfw_concepts": [False, False],
        }
    )
    prov = FalProvider(client=client)
    monkeypatch.setattr(FalProvider, "_download", staticmethod(lambda url: b"X"))
    imgs = prov.generate_image("p", negative="n", aspect_ratio="1:1", n=2)
    assert [i.seed for i in imgs] == [11, 22]  # each image keeps its own seed


def test_fal_rejects_malformed_response():
    prov = FalProvider(client=_FakeFalClient({"unexpected": True}))
    with pytest.raises(ValueError):
        prov.generate_image("p", negative="n", aspect_ratio="1:1")


def test_fal_download_rejects_non_http():
    with pytest.raises(ValueError):
        FalProvider._download("file:///etc/passwd")
