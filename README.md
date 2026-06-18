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

### Easiest: the clickable control panel

```bash
source .venv/bin/activate
python -m avatar_studio.ui.studio      # serves on :7860
```
From your laptop, tunnel in (don't expose it publicly) and open the browser:
```bash
ssh -L 7860:localhost:7860 user@your-vm   # then http://localhost:7860
```
Tab 1: upload your photos + voice clip and click **Train**. Tab 2: generate a
reference face and click **Use as reference**. Tab 3: chat and get a talking
video back.

### Or the command line

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

## Creator Studio (multi-persona content engine)

Layered on the core above is a SFW **creator + commerce** engine: manage multiple
personas trained on your own likeness and generate on-brand content for several
channels, with **every output passing the same safety gates**.

Channels (all clothed / SFW; the media gate fails closed on each):

| Channel | Endpoint | Output |
|---|---|---|
| Lifestyle / beach | `POST /generate` (`lifestyle`) | photoreal image batches in platform sizes |
| TikTok | `POST /generate` (`tiktok`) | 9:16 video (frame-gated) + hook/caption, trend hook |
| Product / dropship | `POST /generate/product-ad` | persona models a product + ad copy |
| Meta ads | `POST /generate/meta-ad` | ad-set draft: image variants × copy variants |

Generation runs on **hosted APIs** (fal.ai by default — Flux image gen, Flux LoRA
training, Kling image-to-video). Set `AVATAR_PROVIDER=fal` and `FAL_KEY`. Use
`AVATAR_PROVIDER=fake` for offline/dev. Personas, products, and a safety-screened
content queue live in a local SQLite store (`AVATAR_DB_URL`), structured to move to
Postgres + object storage later.

Persona / content endpoints: `POST/GET /personas`, `POST /personas/{id}/train`,
`POST /products`, `POST /generate*`, `GET /content`, `POST /content/{id}/review`.
Generated content lands in `review_status=pending`; **nothing publishes without an
explicit human approval**. Publishing to TikTok/Meta is scaffolded but deferred —
it refuses to post un-approved content and stays in dry-run until you complete
TikTok's audit / Meta's App Review + Business Verification.

### Dashboard (Next.js)

```bash
uvicorn avatar_studio.api.app:app --port 8000      # backend
cd dashboard && npm install && npm run dev          # http://localhost:3000
```

Manage personas, run generation batches, and work the **review queue** (approve/
reject each asset, with its SFW status shown). The browser only talks to the
backend via a proxy, so provider keys never reach the client.

See `PLAN.md` for the full build plan and `reviews/research-fal-meta-tiktok.md` for
the API specifics (and the items to verify before spending on live generation).

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
