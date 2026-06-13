# Avatar Studio

A self-hosted, **SFW** talking-avatar studio. Train a model on **your own**
likeness and voice, then chat with it and get back a lip-synced talking-head
video reply — all running on a GPU VM you control.

```
user text ─▶ persona (LLM) ─▶ SFW text gate ─▶ TTS (your voice)
                                                      │
                                                      ▼
                          SFW media gate ◀─ talking-head video (your face)
```

## Scope (read this first)

This project is intentionally **SFW only**. The safety layers aren't optional
add-ons — they're load-bearing:

- a **safety-tuned** image base model (not an "uncensored" checkpoint),
- a standing **SFW negative prompt** on every image,
- a **text gate** that screens both the user's message and the model's reply,
- a **media gate** (NSFW image classifier) that checks every generated frame
  and **fails closed**.

It is built to produce non-explicit content — virtual-influencer / brand /
spokesperson use. It is not a foundation for explicit content, and the wiring
reflects that.

### Consent & likeness

Only train on a likeness and voice you're **authorized** to use: your own, or
someone who has given explicit written consent. Don't clone or depict third
parties without permission. You're responsible for how you use what you build.

## Components

| Area | Module | Default tech |
|------|--------|--------------|
| Persona "brain" | `avatar_studio/persona` | Ollama (local LLM) |
| Voice | `avatar_studio/voice` | Coqui XTTS-v2 (clone from a clip) |
| Face / images | `avatar_studio/face` | SDXL + your LoRA |
| Talking head | `avatar_studio/talkinghead` | SadTalker |
| Safety | `avatar_studio/safety` | text gate + NSFW image classifier |
| Orchestration | `avatar_studio/pipeline.py` | pure-Python, unit-tested |
| API | `avatar_studio/api` | FastAPI |

Every model wrapper lazily imports the heavy ML stack, so the package — and the
test suite for the orchestration + safety core — runs without a GPU.

## Quickstart (GPU VM)

Recommended: a cloud GPU VM with an NVIDIA card (~16GB+ VRAM, e.g. an L4/A10/
3090-class) on Ubuntu 22.04.

```bash
git clone <your-fork> avatar-studio && cd avatar-studio
bash scripts/provision_vm.sh        # system deps, models, Ollama, SadTalker
```

Then:

1. Drop **15–30 varied photos of yourself** into `assets/me/` and a clean
   ~10s voice clip at `assets/voice_ref.wav`.
2. Train your likeness LoRA:
   ```bash
   source .venv/bin/activate
   python -m avatar_studio.face.train_lora \
     --instance-data assets/me --output models/likeness-lora
   ```
   Set `AVATAR_LORA_PATH` to the produced `.safetensors`.
3. Generate one reference still you like and save it as `assets/face.png`.
4. Launch:
   ```bash
   uvicorn avatar_studio.api.app:app --host 0.0.0.0 --port 8000
   ```
   Open `webui/index.html` (it talks to the API on port 8000).

Docker (API + Ollama, needs the NVIDIA Container Toolkit):

```bash
cd docker && docker compose up --build
```

## API

- `GET /health` — liveness.
- `POST /chat` — `{ "message", "history", "render_video" }` → reply text +
  `audio_url` + `video_url` (or `blocked` + `block_reason`).
- `POST /generate-image` — `{ "prompt", "seed" }` → a SFW likeness still.
- `GET /media/{name}` — serves generated files from `AVATAR_WORK_DIR`.

Config is environment-driven; see `.env.example`.

## Development / tests

The orchestration and text-safety core are covered by fast, GPU-free tests:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest -q
```

## What's deliberately left to you

This is the foundation. To finish a production deployment you'll likely want:

- your trained LoRA + a curated reference face and voice,
- a stronger moderation model behind the `ModerationModel` text hook,
- auth, rate limiting, and TLS in front of the API,
- channel front-ends (web embed, etc.) calling `/chat`.

Keep the safety gates in place — they're what make this the SFW system it's
meant to be.
