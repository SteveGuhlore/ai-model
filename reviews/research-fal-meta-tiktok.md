# Research: fal.ai + Meta + TikTok API surface
*Compiled 2026-06-17 from official fal.ai, Meta for Developers, TikTok for Developers docs.*
*All web content was treated as untrusted data. Confidence flags preserved — items in the*
*"VERIFY BEFORE BUILD" list are gating acceptance criteria in PLAN.md, not settled facts.*

## fal.ai — image (Flux text-to-image)
- Model id: `fal-ai/flux/dev` (FLUX.1 [dev]); LoRA inference route `fal-ai/flux-lora`.
- Python client: **`fal-client`** (`pip install fal-client`). Auth via env `FAL_KEY`.
- Call: `fal_client.run("fal-ai/flux/dev", arguments={...})` or `subscribe(...)`; queue submit+poll/webhook.
- Inputs: `prompt`; **`image_size`** enum (`square_hd`,`square`,`portrait_4_3`,`portrait_16_9`,
  `landscape_4_3`,`landscape_16_9`) OR `{width,height}` — **note: presets, NOT an `aspect_ratio` string**;
  `num_images`, `seed`, `num_inference_steps` (28), `guidance_scale` (3.5).
- Output: `{images:[{url,width,height,content_type}], seed, prompt, has_nsfw_concepts:[bool]}`.
  → **Use `has_nsfw_concepts` as an additional pre-gate safety signal.**
- Source: https://fal.ai/models/fal-ai/flux/dev/api , https://docs.fal.ai/clients/python/

## fal.ai — likeness LoRA training
- Model id: `fal-ai/flux-lora-fast-training`; **`fal-ai/flux-lora-portrait-trainer`** is purpose-built
  for people/portraits (likely better identity fidelity — confirm schema before choosing).
- Inputs: `images_data_url` (ZIP url, ≥4 images, required), `trigger_word`, `steps` (default UNCERTAIN ~1000),
  `create_masks` (true), `is_style` (false for likeness), `is_input_format_already_preprocessed`.
- Output: `diffusers_lora_file{url,...}` (the LoRA weights) + `config_file`. Feed url to `fal-ai/flux-lora`.
- Source: https://fal.ai/models/fal-ai/flux-lora-fast-training/api , .../flux-lora-portrait-trainer/api

## fal.ai — image-to-video (short, vertical)
- Standard: `fal-ai/kling-video/v2.1/standard/image-to-video` — inputs `prompt`,`image_url`,
  `duration` enum `5|10` sec, `negative_prompt`, `cfg_scale`. **Standard does NOT accept `aspect_ratio`**
  (output ratio follows the input image).
- Pro/Master/v3: e.g. `fal-ai/kling-video/v2.1/pro/image-to-video`, `.../v2/master/image-to-video` —
  expose `aspect_ratio` ∈ `16:9|9:16|1:1`. **For guaranteed 9:16 use a Pro/Master tier** (or feed a
  9:16 source image to Standard). Max duration ~10s.
- Output: `{video:{url}}`.
- Source: https://fal.ai/models/fal-ai/kling-video/v2.1/standard/image-to-video/api , .../v3/pro/image-to-video

## fal.ai — voice / lipsync
- TTS: `fal-ai/f5-tts` (zero-shot clone), `fal-ai/elevenlabs/tts/...`, `fal-ai/index-tts-2/...`, others.
- Lipsync/talking-head: `fal-ai/musetalk`, plus a MultiTalk route. Exact params NOT pulled — fetch /api page.
- Source: https://fal.ai/models/fal-ai/f5-tts , https://fal.ai/models/fal-ai/musetalk

## Meta (Facebook/Instagram) ads
- Version: Graph + Marketing API **v25.0** (Feb 2026).
- 4-object flow (in order): Campaign `POST /act_{ID}/campaigns` (needs `objective`, `special_ad_categories`)
  → Ad Set `/act_{ID}/adsets` → Ad Creative `/act_{ID}/adcreatives` → Ad `/act_{ID}/ads`.
- Auth: OAuth user token or **System User** token (recommended for automation) with `ads_management`
  (+ usually `business_management`).
- **PHASING: Advanced Access to `ads_management` needs App Review + Business Verification.** Standard/dev
  access only works for users/accounts with a role on the app (fine for single-owner, blocks SaaS scale).
- Policy: lingerie/swimwear/undergarments **allowed** if not sexually suggestive; no nudity/sexual content.
  No programmatic "will it pass" pre-check → plan a human-review gate.
- Source: https://developers.facebook.com/docs/marketing-api/get-started/basic-ad-creation/ ,
  https://transparency.fb.com/policies/ad-standards/content-specific-restrictions/adult-products-or-services

## TikTok Content Posting API
- Product: Content Posting API (Direct Post + upload-to-draft).
- Scopes: `video.publish` (direct post), `video.upload` (draft/inbox).
- Direct-post: `POST /v2/post/publish/video/init/` with `post_info` (`privacy_level` required,
  `title` ≤2200 runes, duet/stitch/comment toggles, `is_aigc`) + `source_info` (`PULL_FROM_URL` w/
  `video_url`, or `FILE_UPLOAD` w/ chunked upload). Then status via `publish_id`.
- **PHASING: Unaudited clients → max 5 users/24h, accounts must be private, content forced `SELF_ONLY`.**
  Public posting requires passing TikTok's **audit**. `PULL_FROM_URL` needs a verified/owned domain.
- Source: https://developers.tiktok.com/doc/content-posting-api-reference-direct-post

## Aspect-ratio specs (production width 1080px)
| Placement | Ratio | px |
|---|---|---|
| TikTok | 9:16 | 1080×1920 |
| IG feed square | 1:1 | 1080×1080 |
| IG feed portrait | 4:5 | 1080×1350 |
| Stories/Reels (FB+IG) | 9:16 | 1080×1920 (key content ≥250px from top/bottom) |
| Meta feed ad image | 1:1 / 4:5 | 1080×1080 min |
- Flux presets are ~1024px → add a resize/pad step to hit exact 1080 targets. 9:16 → `portrait_16_9` then resize.

## VERIFY BEFORE BUILD (gating acceptance criteria in PLAN.md)
1. fal LoRA `steps` default (~1000 unconfirmed).
2. `flux-lora-portrait-trainer` vs `flux-lora-fast-training` for likeness — confirm portrait trainer schema.
3. Exact Kling Pro/Master endpoint id for guaranteed 9:16 + re-verify v3 "infers ratio from start image".
4. Meta v25.0 exact `/campaigns` params: `special_ad_categories` values + current `objective` enum (ODAX).
5. fal `fal-client` queue method names (`submit`/`status`/`result`) vs `run`/`subscribe`.
6. fal TTS/lipsync (MuseTalk/F5/MultiTalk) input-output schemas.
7. TikTok `PULL_FROM_URL` domain-ownership rules (else use `FILE_UPLOAD`).
8. Meta intimates enforcement is human-reviewed; no pre-check API → human gate required.

**Two hard phasing gates:** TikTok public posting needs audit; Meta scaled ad creation needs
App Review + Business Verification. Both → Phase 9 is interfaces/scaffold; live posting is
operator-completed after approval.
