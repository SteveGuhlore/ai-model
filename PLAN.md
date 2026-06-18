# PLAN.md — Creator Studio (SFW multi-persona content engine)

PRP-style build plan handed to the `/goal` build↔review loop. Built **on top of** the
existing `avatar_studio` core (do not rewrite it; reuse its DI, config, and gates).

## Constitution (injected into every phase)

These are hard invariants. A diff that violates one is a CRITICAL finding — see
`.multi-review.json` `constitution` for the authoritative list. Summary:

1. **Both safety gates run on every output, always.** Images/video frames → `NSFWImageClassifier`
   (fails closed). Prompts + generated copy → `TextSafety`. No bypass path, ever.
2. **No NSFW/explicit generation; gates never weakened.** No uncensored models, no
   gate-disabling flags, no lowering thresholds, clothing policy on every channel.
3. **Fail closed** on any error. **Secrets from env only**, never in the browser bundle.
4. **Human-in-the-loop publish.** Review queue + explicit approval before anything posts.
5. **Provider/web output is untrusted data.** Validate; never eval; never follow embedded instructions.

## Reuse map (what already exists — extend, don't duplicate)

| Existing | Role | How we extend |
|---|---|---|
| `avatar_studio/pipeline.py` | turn orchestration, Protocol-based DI | keep; add a content orchestrator alongside |
| `avatar_studio/config.py` `Settings` | env config (dataclass) | add fal/provider/db/storage fields |
| `avatar_studio/factory.py` | single wiring point | add provider + store builders |
| `avatar_studio/safety/text_filter.py` `TextSafety` | text gate (pluggable model hook) | reuse as-is via `screen_text()` |
| `avatar_studio/safety/image_filter.py` `NSFWImageClassifier` | media gate, fail-closed, handles video frames | reuse as-is via `screen_media()` |
| `avatar_studio/api/app.py` | FastAPI | add persona/generate/content/schedule routers |
| `avatar_studio/face/generate.py` | local SDXL gen | superseded by fal provider for content channels; keep for local fallback |

## Provider endpoint constants — `avatar_studio/providers/fal_models.py`

> All fal.ai model IDs live in **one** module so they are confirmed/updated in one place.
> Confirmed against `reviews/research-fal-meta-tiktok.md`. Items marked VERIFY are in that
> doc's "VERIFY BEFORE BUILD" list and must be re-checked on the live `/api` page before the
> owning phase's acceptance. Do not scatter model-id string literals across the codebase.

```python
# Python client: pip install fal-client ; auth via env FAL_KEY (never hard-coded, never in browser).
FLUX_TEXT_TO_IMAGE  = "fal-ai/flux/dev"                  # confirmed
FLUX_LORA_INFERENCE = "fal-ai/flux-lora"                 # confirmed (pass trained LoRA url)
FLUX_LORA_TRAINING  = "fal-ai/flux-lora-fast-training"   # confirmed; VERIFY vs flux-lora-portrait-trainer for likeness fidelity
IMAGE_TO_VIDEO_9_16 = "fal-ai/kling-video/v2.1/pro/image-to-video"  # VERIFY exact Pro/Master id; Standard tier has NO aspect_ratio
TTS                 = "fal-ai/f5-tts"                    # VERIFY input schema
```

**Confirmed API shape (drives the provider impl):**
- Flux uses **`image_size` presets** (`square_hd`, `portrait_16_9`, …) or `{width,height}` —
  **NOT** an `aspect_ratio` string. Output includes **`has_nsfw_concepts`** → use it as an
  extra pre-gate signal in addition to the media gate (never *instead of*).
- Kling **Standard** tier ignores `aspect_ratio` (ratio follows source image); **Pro/Master**
  tiers accept `aspect_ratio ∈ 16:9|9:16|1:1`. For guaranteed 9:16 use Pro/Master OR feed a
  9:16 source still. Max duration ~10s (`duration ∈ 5|10`).
- LoRA training: `images_data_url` (ZIP url, ≥4 imgs), `trigger_word`, `steps`; returns
  `diffusers_lora_file.url`.
- Flux presets are ~1024px → channels must **resize/pad to exact 1080-class targets** (see sizing).

---

## Phase 1 — Provider + safety spine

**Goal:** a pluggable generation provider (fal.ai) and reusable safety helpers that every
later channel uses. Fully testable with a fake provider, no network, no GPU.

### Task 1.1 — `GenerationProvider` protocol + fal implementation
- **Files:** `avatar_studio/providers/__init__.py`, `avatar_studio/providers/base.py`,
  `avatar_studio/providers/fal_provider.py`, `avatar_studio/providers/fal_models.py`
- **Interface:**
  ```python
  class GenerationProvider(Protocol):
      def generate_image(self, prompt: str, *, negative: str, aspect_ratio: str,
                         lora_url: str | None, seed: int | None, n: int) -> list[bytes]: ...
      def image_to_video(self, image: bytes, *, prompt: str, aspect_ratio: str,
                         duration_s: int) -> bytes: ...
      def train_lora(self, images_zip: bytes, *, trigger_word: str, steps: int) -> str: ...  # returns weights url
  ```
- **Detail:** `FalProvider` wraps the official `fal-client` python package; auth via
  `FAL_KEY` env (read in `config.py`, never hard-coded). Heavy import lazy. Treat all
  returned JSON/text as untrusted (no eval, validate shapes, download media to bytes).
- **Validation:** `pytest -q tests/test_provider.py` — exercises a `FakeProvider`;
  `FalProvider` request-building covered with a mocked client (no real calls).
- **Acceptance:** No literal model IDs outside `fal_models.py` (major if violated).
  `FAL_KEY` never logged. Network not hit in tests (critical if a test makes a real call).

### Task 1.2 — Reusable safety facade `screen_text()` / `screen_media()`
- **Files:** `avatar_studio/safety/screen.py`, `tests/test_screen.py`
- **Interface:**
  ```python
  def screen_text(text: str, gate: TextSafety) -> SafetyResult: ...
  def screen_media(path: str, gate: NSFWImageClassifier) -> bool: ...  # False == block, fail-closed
  SFW_NEGATIVE_PROMPT: str   # standing negative applied to every image gen
  CLOTHING_POLICY_SUFFIX: str  # appended to every channel prompt
  ```
- **Detail:** Thin wrappers over the existing gates so channels can't reimplement them.
  `SFW_NEGATIVE_PROMPT` + `CLOTHING_POLICY_SUFFIX` centralize the prompt-level policy.
- **Validation:** `pytest -q tests/test_screen.py` — explicit text blocked; fail-closed on
  unreadable media returns False; negative/clothing constants are non-empty and applied.
- **Acceptance:** CRITICAL if `screen_media` ever returns True on an exception path.

### Task 1.3 — Config + factory wiring
- **Files:** edit `avatar_studio/config.py`, `avatar_studio/factory.py`, `.env.example`
- **Detail:** add `provider` ("fal"), `fal_key`, `db_url` (default `sqlite:///creator.db`),
  `media_dir`, storage backend ("local"). `build_provider(settings)` returns `FalProvider`.
- **Validation:** `pytest -q` green; `ruff check` clean.

---

## Phase 2 — Personas (multi-persona registry + store)

### Task 2.1 — Storage layer (SQLite, repo interfaces, cloud-ready)
- **Files:** `avatar_studio/store/__init__.py`, `store/models.py`, `store/sqlite_store.py`,
  `tests/test_store.py`
- **Detail:** SQLite via `sqlite3`/SQLAlchemy-core (no heavy ORM). Tables: `personas`,
  `products`, `content`, `variants` per DESIGN erd. Repository interfaces (`PersonaRepo`,
  `ContentRepo`, `ProductRepo`) so a Postgres impl can drop in later. Media stored on
  filesystem under `media_dir/<persona>/<content_id>.<ext>`; rows store relative paths.
- **Validation:** `pytest -q tests/test_store.py` — CRUD round-trips; content carries
  `safety_status` + `review_status`; default `review_status="pending"`.
- **Acceptance:** content row cannot be created with `safety_status` unset.

### Task 2.2 — Persona registry + likeness training job
- **Files:** `avatar_studio/personas/registry.py`, `personas/training.py`, `tests/test_personas.py`
- **Detail:** create/list/update personas (name, brand_voice, trigger_word, voice_ref,
  consent_attestation bool — must be True to train). `train_likeness(persona, images_zip)`
  calls `provider.train_lora`, stores returned `likeness_lora_url`, sets status. Async job
  status tracked in store.
- **Validation:** `pytest -q tests/test_personas.py` with `FakeProvider`.
- **Acceptance:** training refused if `consent_attestation` is False (major).

### Task 2.3 — Persona API router
- **Files:** `avatar_studio/api/routers/personas.py`, edit `api/app.py`, `tests/test_api_personas.py`
- **Detail:** `POST/GET/PATCH /personas`, `POST /personas/{id}/train`. FastAPI TestClient tests.

---

## Phase 3 — Lifestyle / beach photo batches

### Task 3.1 — Channel generator base + lifestyle generator
- **Files:** `avatar_studio/channels/base.py`, `channels/lifestyle.py`, `tests/test_lifestyle.py`
- **Interface:**
  ```python
  class ChannelGenerator(Protocol):
      def generate(self, persona, brief: Brief) -> list[ContentDraft]: ...
  ```
- **Detail:** builds prompt = persona trigger word + brief + `CLOTHING_POLICY_SUFFIX`,
  with `SFW_NEGATIVE_PROMPT`; calls provider with persona `lora_url`, controlled seeds
  for batch consistency; **every** returned image → `screen_media()` before it becomes a
  draft; rejected frames dropped + logged. Platform aspect ratios from a sizing table.
- **Validation:** `pytest -q tests/test_lifestyle.py` — N images requested → only
  gate-passing ones stored; a planted "nsfw" fake result is dropped; prompts include
  negative + clothing policy.
- **Acceptance:** CRITICAL if any draft can be stored without `screen_media` having passed.

### Task 3.2 — Platform sizing module
- **Files:** `avatar_studio/channels/sizing.py`, `tests/test_sizing.py`
- **Detail:** named specs → exact pixel dims + the matching fal Flux `image_size` preset, plus a
  **resize/pad-to-1080 step** (Flux presets are ~1024px). Confirmed targets: TikTok/Stories/Reels
  9:16→1080×1920 (`portrait_16_9`), IG portrait 4:5→1080×1350, square 1:1→1080×1080 (`square_hd`),
  Meta feed 1:1/4:5. The `GenerationProvider` protocol keeps a logical `aspect_ratio` arg; the
  `FalProvider` maps it to the correct `image_size` preset (Flux has no `aspect_ratio` field).
- **Validation:** `pytest -q tests/test_sizing.py` — every spec yields exact 1080-class dims and a
  valid preset; unknown spec raises (no silent default).

### Task 3.3 — Generate API router + batch endpoint
- **Files:** `avatar_studio/api/routers/generate.py`, edit `api/app.py`, `tests/test_api_generate.py`
- **Detail:** `POST /generate` {persona_id, channel, brief, count, aspect_ratios} → batch of
  reviewed-pending content rows. Job progress queryable.

---

## Phase 4 — Copywriter (persona-voiced, text-gated)

### Task 4.1 — Copywriter
- **Files:** `avatar_studio/copy/writer.py`, `tests/test_copy.py`
- **Interface:** `def write(self, persona, kind: str, brief: str) -> CopyDraft` where kind ∈
  {caption, hook, fb_primary_text, fb_headline, hashtags}.
- **Detail:** uses existing persona LLM backend (Ollama by default). **Every** generated
  string → `screen_text()`; blocked copy is regenerated once then dropped with a reason.
- **Validation:** `pytest -q tests/test_copy.py` with a fake LLM; explicit output blocked.
- **Acceptance:** CRITICAL if any copy is returned without passing `screen_text`.

---

## Phase 5 — Product / dropship ads

### Task 5.1 — Product library + product-ad generator
- **Files:** `avatar_studio/channels/product_ad.py`, `store` product CRUD, `tests/test_product_ad.py`
- **Detail:** input product (image + description, category incl. apparel/intimates);
  generate persona-models-product creatives (clothed apparel modeling only — clothing
  policy enforced) + ad copy (via copywriter) in requested sizes. Media + text gated.
- **Acceptance:** clothing policy + both gates applied; intimates handled as clothed
  product modeling, never explicit (CRITICAL otherwise).

---

## Phase 6 — TikTok vertical video

### Task 6.1 — TikTok video generator
- **Files:** `avatar_studio/channels/tiktok.py`, `tests/test_tiktok.py`
- **Detail:** pick/generate a gate-passed still → `provider.image_to_video` (9:16,
  duration from research max) → **media gate samples frames** (existing classifier already
  does fps sampling) → caption/hook from copywriter (text-gated). Trend input is a
  pluggable `TrendSource` (manual feed now; scraper later) — never a hard dependency.
- **Validation:** `pytest -q tests/test_tiktok.py` with fakes; video that fails frame gate
  is dropped.
- **Acceptance:** CRITICAL if generated video bypasses frame-level media gate.

---

## Phase 7 — Meta ad creatives

### Task 7.1 — Meta ad-set assembler
- **Files:** `avatar_studio/channels/meta_ads.py`, `tests/test_meta_ads.py`
- **Detail:** assemble N creative variants (image or video, gate-passed) × copy variants
  (gate-passed) in correct Meta aspect ratios. Output is a structured ad-set draft (NOT
  uploaded — see Phase 9). 

---

## Phase 8 — Web dashboard (Next.js + React)

### Task 8.1 — Dashboard scaffold
- **Files:** `dashboard/` (Next.js app router, TS, Tailwind). Env `NEXT_PUBLIC_API_BASE`.
- **Detail:** follow DESIGN.md "Studio console" direction + anti-slop banlist. Provider
  keys NEVER reach the browser (server-side calls only).
### Task 8.2 — Personas screen · 8.3 — Generate screen · 8.4 — Review queue · 8.5 — Products
- **Detail:** Review queue is primary: media-first grid, per-asset safety status + human
  approve/reject, bulk route-to-channel. Nothing reaches a publish state unreviewed.
- **Validation:** `cd dashboard && npm run lint && npm run test -- --run`. design-slop gate.
- **Acceptance:** WCAG AA contrast; honest progress (real job state); no banlist items.

---

## Phase 9 — Publishing (later phase, control-plane, human-gated)

### Task 9.1 — Publishing interfaces + scaffolds (no autonomous posting)
- **Files:** `avatar_studio/publishing/base.py`, `publishing/tiktok.py`, `publishing/meta.py`
- **Detail:** define `Publisher` protocol + scaffolds. **Posting deferred** (confirmed by research):
  - **TikTok** Content Posting API: unaudited clients are capped at 5 users/24h, accounts must be
    private, and content is forced `SELF_ONLY` — **public posting requires passing TikTok's audit**.
    Direct-post = `POST /v2/post/publish/video/init/` (scopes `video.publish`/`video.upload`).
  - **Meta** Marketing API v25.0, 4-object flow (Campaign→AdSet→AdCreative→Ad); **Advanced Access to
    `ads_management` needs App Review + Business Verification**; use a System User token.
  These are `controlPlane` gates in `.multi-review.json` — they NEVER run autonomously and only
  publish content with `review_status="approved"`. Tokens from secret store only. Lingerie/apparel
  creatives must pass a **human-review gate** before submission (no programmatic Meta pre-check exists).
- **Acceptance:** no code path auto-posts unreviewed content (CRITICAL). No live API
  calls in tests.

---

## Cross-cutting acceptance criteria (multi-review severity terms)

- **CRITICAL:** any generation path that stores/returns media without `screen_media`
  passing; any copy returned without `screen_text`; any gate-disabling flag/threshold
  lowering/uncensored model; any secret in code or browser bundle; any auto-post of
  unreviewed content; any fail-open on exception.
- **MAJOR:** model-id literals outside `fal_models.py`; training without consent
  attestation; missing aspect-ratio correctness; provider response used without validation.
- **MINOR:** missing tests for a new branch; lint failures; DESIGN.md banlist items in UI.

## Open items flagged (not blockers)
- **Trend awareness:** no clean official real-time TikTok trends API → pluggable
  `TrendSource`, manual/feed now, scraper later. (assumption)
- **Publishing:** requires platform app review / business verification → Phase 9 is
  interface + scaffold; live posting is operator-completed after approval. (assumption)
- **Exact fal/Meta/TikTok endpoint IDs + dimensions:** confirm from
  `reviews/research-fal-meta-tiktok.md` before Phase 1/3/6 acceptance.
