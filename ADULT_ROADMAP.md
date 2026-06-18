# Adult Creator Roadmap

Research date: 2026-06-18.

This roadmap assumes two parallel lanes:

- SFW lane: public/social/ad content, TikTok/Meta/product ads, broad discovery.
- Adult lane: Fanvue, Telegram paid packs, CRM-managed custom requests, and later
  OFAuth-backed OnlyFans-style operations.

The adult lane is not a global override. It is an explicit workflow with consent,
age verification, AI disclosure, platform eligibility, payment state, and human
review gates.

## Current Shipped State

- SFW Creator Studio exists with personas, provider abstraction, async jobs,
  content store, review queue, channel generators, and dashboard.
- Adult policy preflight exists at `POST /adult/policy-check`.
- `AVATAR_CONTENT_MODES=sfw,adult` enables both lanes.
- Existing SFW endpoints still use SFW gates.
- No live adult generation or delivery exists yet.

## Research Summary

### Fanvue

Source: https://www.fanvue.com/

Fanvue publicly markets itself as an AI monetisation platform. Its homepage lists
features including payments, payouts, checkout links, monthly subscriptions,
paywalled content, AI analytics, AI voice calls, AI voice notes, and "App Store &
Open API" described as an open platform for AI builders.

What we can likely do:

- Treat Fanvue as the first adult subscription platform target.
- Build a connector interface now.
- Add a Fanvue connector stub until API credentials/docs are available.
- Prepare content packages with AI disclosure metadata, caption, price, preview,
  asset IDs, and review status.

What needs verification with real docs/account access:

- Auth model and token lifecycle.
- Upload endpoints and media size limits.
- Post/paywall/message endpoints.
- Whether API supports PPV messages, subscriptions, checkout links, analytics,
  and AI-specific disclosure fields.
- Whether API can fetch fans/subscribers and purchase events.

### Telegram

Sources:

- https://core.telegram.org/bots/payments-stars
- https://core.telegram.org/bots/api

Telegram has the clearest official payment path. Digital goods sold inside
Telegram apps must use Telegram Stars with currency `XTR`. The expected flow is:
`sendInvoice`, receive `pre_checkout_query`, respond with
`answerPreCheckoutQuery`, wait for `successful_payment`, store the
`telegram_payment_charge_id`, then deliver goods.

The Bot API also supports paid media concepts such as `PaidMediaInfo`,
`PaidMediaPhoto`, `PaidMediaVideo`, `InputPaidMediaPhoto`, and
`InputPaidMediaVideo`.

What we can do first:

- Telegram bot storefront for approved content packs.
- Terms/age-gate acknowledgement before purchase.
- Invoice creation using Stars.
- Payment-state machine.
- Delivery only after `successful_payment`.
- CRM sync for buyer, offer, payment charge ID, content IDs, and delivery receipt.
- Refund/support tracking.

What to avoid initially:

- Fully autonomous generation for custom adult requests.
- Delivery before payment confirmation.
- Delivery of unapproved content.
- Third-party payment providers inside Telegram apps for digital goods.

### OFAuth / OnlyFans-style Integrations

Sources:

- https://docs.ofauth.com/introduction/onlyfans-api
- https://docs.ofauth.com/quickstart
- https://docs.ofauth.com/api-reference/core/overview
- https://docs.ofauth.com/llms.txt

OFAuth documents that OnlyFans does not provide official external developer API
access. OFAuth handles the volatile pieces: signing rules, authentication flows,
proxying, session lifecycle, rate limits, connection expiry, and webhooks.

OFAuth docs list Access API areas for chats/messages, subscribers,
subscriptions, users, posts, stories, media/vault, earnings, analytics,
promotions, user lists, upload, and realtime/system webhooks.

What we can do:

- Treat OnlyFans as provider-backed, not scraped.
- Store OFAuth connection IDs in the CRM, not this generation service.
- Build connector stubs around capabilities: list subscribers, list chats,
  send message, create post, upload media, get analytics, receive webhooks.
- Use async queues, retry/circuit breakers, and stale-while-revalidate caching.

What not to do:

- Do not scrape logged-in web sessions.
- Do not build direct signing/reverse-engineering.
- Do not store platform credentials in this repo.

### Fansly / Hidden / SextPanther / Others

Current public official API documentation was not clearly discoverable in this
pass. Treat these as later connectors with capability flags:

- official API: implement directly after docs/credentials are confirmed.
- approved provider API: integrate provider-side.
- no reliable API: manual import/export only.

## Product Architecture

```text
CRM repo
  fans/subscribers
  platform connectors
  payments and purchases
  conversations
  campaigns and analytics
  Telegram bot
  Fanvue/OFAuth credentials
  delivery jobs

Avatar Studio repo
  personas and likeness metadata
  SFW generation
  adult policy preflight
  adult generation jobs later
  content safety/platform eligibility
  media storage references
  review queue
```

The CRM should call this repo as a generation/policy service. This repo should
not own subscriber billing, platform tokens, or CRM campaign state.

## Roadmap

### PR 3 - Platform Capability Model

Goal: represent what each platform can do without making live calls.

Files:

- `avatar_studio/platforms/base.py`
- `avatar_studio/platforms/fanvue.py`
- `avatar_studio/platforms/telegram.py`
- `avatar_studio/platforms/ofauth.py`
- `tests/test_platforms.py`
- `PLATFORM_RESEARCH.md` or keep this document updated

Capabilities:

- `supports_adult_content`
- `supports_ai_creator`
- `supports_paid_media`
- `supports_messages`
- `supports_posts`
- `supports_subscribers`
- `supports_analytics`
- `requires_ai_disclosure`
- `requires_human_review`
- `requires_confirmed_payment`

### PR 4 - Telegram Approved-Content Sales

Goal: build the safest first monetization path.

State machine:

```text
draft_offer -> policy_checked -> invoice_sent -> precheckout_seen
-> payment_confirmed -> delivery_queued -> delivered -> support/refund_optional
```

Rules:

- Only approved content can be attached to an offer.
- Only adult-policy-passed offers can be sold in the adult lane.
- Delivery requires confirmed payment.
- Telegram charge IDs are stored for support/refunds.
- Terms/age acknowledgement is required before purchase.

### PR 5 - Adult Generate Pack Endpoint

Goal: generate review-pending adult packs for Fanvue/Telegram.

Endpoint:

`POST /adult/generate-pack`

Behavior:

- Runs `AdultContentPolicy` first.
- Uses async `JobRunner`.
- Stores outputs with adult content metadata.
- Does not deliver or publish.
- Requires human approval before CRM delivery.

### PR 6 - Fanvue Connector

Goal: integrate after real Fanvue API credentials/docs are available.

Likely operations:

- Upload media.
- Create paywalled post or paid message.
- Read subscriber/fan data.
- Fetch purchase/earnings analytics.
- Sync delivery/publish state back to CRM.

### PR 7 - OFAuth Connector For CRM

Goal: CRM-side integration, not generation-service ownership.

Operations:

- Create OFAuth Link session.
- Store connection ID.
- Read subscribers/chats/analytics.
- Send approved content as message/post if allowed by provider endpoints.
- Receive connection/session webhooks.

### PR 8 - Autonomous Offer Engine

Goal: automate offers, not unchecked generation.

Allowed automation:

- Segment buyers.
- Pick already-approved content packs.
- Send timed offers.
- Follow up after non-purchase.
- Route custom requests into review.

Blocked automation:

- Generating adult media and delivering it without review.
- Sending content before payment confirmation.
- Impersonating real third parties.
- Platform posting without verified API permission.

## Suggested Offers

- Free SFW teaser -> adult paid pack.
- Telegram starter pack.
- Fanvue welcome bundle.
- Weekly themed drop.
- Custom request quote.
- Voice-note upsell.
- High-spender private bundle.
- Re-engagement discount.

## Next Build Prompt

```text
Continue in C:\Users\alexa\Downloads\Ai Model on branch feat/adult-mode-policy-spine.
Implement PR 3: Platform Capability Model.

Requirements:
- Keep SFW and adult lanes parallel: AVATAR_CONTENT_MODES=sfw,adult.
- Do not build live network integrations.
- Add avatar_studio/platforms/base.py with PlatformName, PlatformCapability,
  PlatformPolicy, DeliveryState, and helpers.
- Add stubs for fanvue, telegram, and ofauth with research-backed capability flags.
- Add tests proving Telegram delivery requires confirmed payment and approved
  content, and Fanvue/OFAuth capabilities are explicit.
- Update ADULT_ROADMAP.md if the implementation changes the plan.
- Run python -m pytest -q and .venv/Scripts/python.exe -m ruff check avatar_studio tests.
- Commit, push, and update PR #2.
```
