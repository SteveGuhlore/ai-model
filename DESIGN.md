# DESIGN.md — Creator Studio (SFW multi-persona content engine)

> Builds on the existing `avatar_studio` core. This document covers product taste,
> the dashboard aesthetic, and the **anti-slop banlist** the design-slop gate enforces.
> The hard safety invariants live in `.multi-review.json` (`constitution`) and `PLAN.md`.

## What this is

A control panel for an operator running one or more **SFW virtual-influencer personas**
trained on their own likeness. From one place they: manage personas, generate
photoreal lifestyle/beach photo batches, produce product/apparel ad creatives,
make TikTok vertical videos, assemble Meta ad sets, review a safety-screened
content queue, and (later) schedule/publish.

It is **not** an explicit-content tool. Every output passes the SFW gates. The UI
must make that visible, not hidden — a safety status on every asset.

## Users & primary jobs

- **Operator/creator** (primary): "generate 20 on-brand beach shots for Persona A,
  pick the keepers, push 6 to a TikTok batch and 4 to a Meta ad set."
- **Brand/dropship client** (secondary, later): supplies a product, gets back
  persona-modeled ad creatives + copy in the right sizes.

## Taste / brand direction

Two aesthetic families to remix (pick the lean during build, don't blend muddily):

1. **"Studio console" (recommended)** — calm, dark-neutral operator tool. Think
   Linear / Vercel dashboard: high-contrast type, restrained accent color, dense
   but breathable tables, media-first cards. Lets the *generated imagery* be the
   color. Best for a tool you stare at for hours.
2. **"Creator-bright"** — lighter, social-app energy (Instagram-creator-studio
   adjacent): rounded cards, soft shadows, one warm accent. Friendlier, slightly
   more consumer. Risk: competes with the imagery for attention.

Default to **Studio console**. Imagery is the hero; chrome stays quiet.

### Tokens (seed; refine in build)
- Surface: near-black/neutral-950 base, neutral-900 panels, neutral-800 borders.
- Accent: a single saturated hue (e.g. indigo/violet) for primary actions + active state only.
- Type: one humanist sans (Inter/Geist-class), tight tracking on headings.
- Radius: consistent 8–12px; one elevation system, no random shadows.
- Status colors: green=safe/approved, amber=needs review, red=blocked — used *only* for status.

## Key screens

1. **Personas** — grid of persona cards (avatar, name, brand voice, training status).
   Create/edit; kick off likeness LoRA training; attach voice ref.
2. **Generate** — pick persona + channel (lifestyle / product ad / TikTok / Meta ad),
   set prompt/brief + count + aspect ratios, run a batch. Live progress.
3. **Review queue** — the heart of the app. Media-first grid; each asset shows
   **safety status** (auto) and a human **approve/reject**. Bulk select → route to
   a channel batch or schedule. Nothing leaves "review" to "publish" unreviewed.
4. **Products** — dropship product library; "make ad with Persona X".
5. **Schedule** (later) — calendar of queued posts per channel.

## Motion / polish
- Motion is functional only: queue items settle in, progress is honest (real job
  state, never a fake spinner that lies about completion). Respect reduced-motion.
- Media loads with a stable skeleton at the final aspect ratio — no layout shift.

## Anti-slop banlist (design-slop gate enforces)

The dashboard must not look like default-template AI slop. Banned unless explicitly justified:

- ❌ Purple→pink 45° hero gradients; glowing gradient blobs as "design".
- ❌ Emoji used as UI icons in production chrome.
- ❌ Centered hero + three feature cards + "Powered by AI" filler.
- ❌ Unlabeled icon-only buttons for destructive/important actions.
- ❌ Fake/optimistic progress bars; spinners with no real job state behind them.
- ❌ Generic stock-y empty states ("Nothing here yet 🎉"); empty states must teach the next action.
- ❌ Inconsistent radii/shadows/spacing (pick the scale, hold it).
- ❌ Low-contrast gray-on-gray text failing WCAG AA.
- ❌ Tables that overflow horizontally on the operator's main viewport.

## Imagery quality bar (the actual product)

The generated content — not the chrome — is judged hardest. Direction the channel
generators must hit (encoded as prompt policy + review criteria, **all SFW/clothed**):

- Photoreal, not "AI-render": natural skin texture and lighting, plausible anatomy
  and hands, no plastic sheen, no warped backgrounds.
- Character **consistency** across a batch (same persona reads as the same person):
  trigger word + LoRA + controlled seeds.
- Clothed/swimwear/apparel only. The clothing-enforcement prompt policy and the
  media gate are non-negotiable and apply to every channel.
- Platform-correct framing: subject placed for 9:16 / 4:5 / 1:1 crops without cutting heads.
