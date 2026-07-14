"""FastAPI service exposing the SFW avatar.

Endpoints:
  GET  /health             liveness
  POST /chat               message -> persona reply + spoken talking-head video
  POST /generate-image     prompt  -> a SFW likeness still
  GET  /media/{name}       serve generated audio/video/images from work_dir

Backends are constructed lazily on first use so the server can boot (and
/health can pass) before models are warmed.
"""

from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from avatar_studio.config import Settings
from avatar_studio.factory import build_face_generator, build_pipeline

settings = Settings.from_env()
app = FastAPI(title="Avatar Studio (SFW)", version="0.1.0")

# Creator-studio routers (personas, generation, content review, jobs).
from avatar_studio.api.routers import adult as _adult_router  # noqa: E402
from avatar_studio.api.routers import generate as _generate_router  # noqa: E402
from avatar_studio.api.routers import jobs as _jobs_router  # noqa: E402
from avatar_studio.api.routers import personas as _personas_router  # noqa: E402

app.include_router(_personas_router.router)
app.include_router(_generate_router.router)
app.include_router(_jobs_router.router)
app.include_router(_adult_router.router)

_pipeline = None
_face = None


def pipeline():
    global _pipeline
    if _pipeline is None:
        _pipeline = build_pipeline(settings)
    return _pipeline


def face_generator():
    global _face
    if _face is None:
        _face = build_face_generator(settings)
    return _face


def _as_url(path: str | None) -> str | None:
    if not path:
        return None
    return f"/media/{os.path.basename(path)}"


class ChatIn(BaseModel):
    message: str
    history: list[dict] = []
    render_video: bool = True


class ChatOut(BaseModel):
    text: str
    blocked: bool
    block_reason: str = ""
    audio_url: str | None = None
    video_url: str | None = None


class ImageIn(BaseModel):
    prompt: str
    seed: int | None = None


class ImageOut(BaseModel):
    blocked: bool
    image_url: str | None = None
    reason: str = ""


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatOut)
def chat(inp: ChatIn):
    result = pipeline().handle_turn(inp.message, inp.history, inp.render_video)
    return ChatOut(
        text=result.text,
        blocked=result.blocked,
        block_reason=result.block_reason,
        audio_url=_as_url(result.audio_path),
        video_url=_as_url(result.video_path),
    )


@app.post("/generate-image", response_model=ImageOut)
def generate_image(inp: ImageIn):
    import uuid

    from avatar_studio.safety.image_filter import NSFWImageClassifier
    from avatar_studio.safety.screen import screen_media, screen_text
    from avatar_studio.safety.text_filter import TextSafety

    # Screen the prompt first - parity with the channel build_prompt path.
    if screen_text(inp.prompt, TextSafety()).blocked:
        return ImageOut(blocked=True, reason="input:sexual_explicit")

    os.makedirs(settings.work_dir, exist_ok=True)
    out_path = os.path.join(settings.work_dir, f"img_{uuid.uuid4().hex[:12]}.png")
    face_generator().generate(inp.prompt, out_path, seed=inp.seed)

    guard = NSFWImageClassifier(settings.nsfw_classifier, settings.nsfw_threshold, settings.device)
    # screen_media fails closed: a classifier error blocks rather than 500s.
    if not screen_media(out_path, guard):
        if os.path.exists(out_path):
            os.remove(out_path)
        return ImageOut(blocked=True, reason="output:media_nsfw")
    return ImageOut(blocked=False, image_url=_as_url(out_path))


@app.get("/media/{name}")
def media(name: str):
    # Prevent path traversal; only serve flat files from work_dir.
    safe = os.path.basename(name)
    path = os.path.join(settings.work_dir, safe)
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="not found")
    return FileResponse(path)


@app.get("/media/{persona_id}/{name}")
def content_media(persona_id: str, name: str):
    # Generated content media lives under media_dir/<persona_id>/<file>.
    # basename() both segments so no '..' or nested path can escape media_dir.
    safe_dir = os.path.basename(persona_id)
    safe = os.path.basename(name)
    path = os.path.join(settings.media_dir, safe_dir, safe)
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="not found")
    return FileResponse(path)

