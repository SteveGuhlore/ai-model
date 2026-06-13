import os

from avatar_studio.pipeline import SAFE_FALLBACK, AvatarPipeline
from avatar_studio.safety.text_filter import TextSafety


class FakePersona:
    def __init__(self, text):
        self.text = text

    def reply(self, user_message, history):
        return self.text


class FakeTTS:
    def synthesize(self, text, out_path):
        with open(out_path, "w") as f:
            f.write("audio")
        return out_path


class FakeHead:
    def render(self, face_image, audio_path, out_path):
        with open(out_path, "w") as f:
            f.write("video")
        return out_path


class FakeMediaSafety:
    def __init__(self, sfw=True):
        self.sfw = sfw

    def is_sfw(self, media_path):
        return self.sfw


def make_pipe(reply_text, tmp_path, sfw=True):
    return AvatarPipeline(
        persona=FakePersona(reply_text),
        tts=FakeTTS(),
        head=FakeHead(),
        face_image="assets/face.png",
        text_safety=TextSafety(),
        media_safety=FakeMediaSafety(sfw),
        work_dir=str(tmp_path),
    )


def test_happy_path(tmp_path):
    p = make_pipe("Sure, happy to help with that!", tmp_path)
    r = p.handle_turn("hello there", [])
    assert not r.blocked
    assert r.text.startswith("Sure")
    assert os.path.exists(r.audio_path)
    assert os.path.exists(r.video_path)


def test_blocks_explicit_input(tmp_path):
    p = make_pipe("anything", tmp_path)
    r = p.handle_turn("send nudes please", [])
    assert r.blocked
    assert r.text == SAFE_FALLBACK
    assert r.block_reason.startswith("input:")


def test_blocks_explicit_output(tmp_path):
    p = make_pipe("here are some nudes for you", tmp_path)
    r = p.handle_turn("hello", [])
    assert r.blocked
    assert r.block_reason.startswith("output:")


def test_blocks_nsfw_media(tmp_path):
    p = make_pipe("a totally clean reply", tmp_path, sfw=False)
    r = p.handle_turn("hello", [])
    assert r.blocked
    assert r.block_reason == "output:media_nsfw"


def test_skip_video(tmp_path):
    p = make_pipe("clean reply here", tmp_path)
    r = p.handle_turn("hello", [], render_video=False)
    assert not r.blocked
    assert r.video_path is None
    assert os.path.exists(r.audio_path)
