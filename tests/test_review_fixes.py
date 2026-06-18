"""Regression tests for multi-review findings P0–P3 + input bounds."""

import os

import pytest

from avatar_studio.pipeline import SAFE_FALLBACK, AvatarPipeline
from avatar_studio.providers.fal_provider import FalProvider, _host_allowed
from avatar_studio.safety.text_filter import TextSafety


# --- P0: blocked NSFW media is deleted, not left on disk -----------------
class FakeTTS:
    def synthesize(self, text, out_path):
        with open(out_path, "w") as f:
            f.write("audio")
        return out_path


class FakeHead:
    def render(self, face, audio, out_path):
        with open(out_path, "w") as f:
            f.write("video")
        return out_path


class FakePersona:
    def reply(self, msg, history):
        return "a totally clean reply"


def _pipe(tmp_path, sfw, raise_on_render=False):
    class Head(FakeHead):
        def render(self, face, audio, out_path):
            if raise_on_render:
                raise RuntimeError("render exploded")
            return super().render(face, audio, out_path)

    class Media:
        def is_sfw(self, p):
            return sfw

    return AvatarPipeline(
        persona=FakePersona(),
        tts=FakeTTS(),
        head=Head(),
        face_image="assets/face.png",
        text_safety=TextSafety(),
        media_safety=Media(),
        work_dir=str(tmp_path),
    )


def test_blocked_media_is_removed_from_disk(tmp_path):
    p = _pipe(tmp_path, sfw=False)
    r = p.handle_turn("hello", [])
    assert r.blocked and r.text == SAFE_FALLBACK
    # nothing left behind in the servable work_dir
    assert os.listdir(tmp_path) == []


def test_exception_midturn_leaves_no_partial_media(tmp_path):
    p = _pipe(tmp_path, sfw=True, raise_on_render=True)
    with pytest.raises(RuntimeError):
        p.handle_turn("hello", [])
    assert os.listdir(tmp_path) == []


def test_happy_path_keeps_media(tmp_path):
    p = _pipe(tmp_path, sfw=True)
    r = p.handle_turn("hello", [])
    assert not r.blocked
    assert os.path.exists(r.video_path)


# --- P3: _download SSRF host allowlist + scheme --------------------------
def test_host_allowlist_blocks_metadata_ip():
    assert _host_allowed("169.254.169.254") is False
    assert _host_allowed("127.0.0.1") is False
    assert _host_allowed("10.0.0.5") is False


def test_host_allowlist_allows_fal_cdn():
    assert _host_allowed("v3.fal.media") is True
    assert _host_allowed("fal.media") is True
    assert _host_allowed("evil.com") is False


def test_download_rejects_non_https():
    with pytest.raises(ValueError):
        FalProvider._download("http://fal.media/x.png")
    with pytest.raises(ValueError):
        FalProvider._download("file:///etc/passwd")


def test_download_rejects_disallowed_host():
    with pytest.raises(ValueError):
        FalProvider._download("https://169.254.169.254/latest/meta-data/")


def test_host_allowlist_rejects_public_ip_literal():
    # A bare public IP is never a fal CDN host (closes the public-IP escape hatch).
    assert _host_allowed("93.184.216.34") is False


def test_resolve_safe_rejects_private_and_allows_public(monkeypatch):
    import socket

    from avatar_studio.providers import fal_provider

    monkeypatch.setattr(
        socket, "getaddrinfo", lambda *a, **k: [(2, 1, 6, "", ("10.0.0.5", 0))]
    )
    assert fal_provider._resolve_safe("rebind.fal.media") is False
    monkeypatch.setattr(
        socket, "getaddrinfo", lambda *a, **k: [(2, 1, 6, "", ("93.184.216.34", 0))]
    )
    assert fal_provider._resolve_safe("v3.fal.media") is True


def test_download_does_not_follow_redirect_to_metadata(monkeypatch):
    # A 302 from an allowed host pointing at the metadata IP must NOT be followed.
    from avatar_studio.providers import fal_provider

    monkeypatch.setattr(fal_provider, "_resolve_safe", lambda host: True)
    calls = {"n": 0}

    class FakeResp:
        is_redirect = True
        status_code = 302
        headers = {"Location": "https://169.254.169.254/latest/meta-data/"}

        def close(self):
            pass

    import requests

    def fake_get(url, **kwargs):
        calls["n"] += 1
        assert kwargs.get("allow_redirects") is False  # redirects handled manually
        return FakeResp()

    monkeypatch.setattr(requests, "get", fake_get)
    with pytest.raises(ValueError):
        FalProvider._download("https://v3.fal.media/img.png")
    assert calls["n"] == 1  # never issued the second GET to the metadata host
