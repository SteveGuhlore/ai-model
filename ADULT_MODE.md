# Adult Mode

Adult mode is now a first-class content lane that runs alongside SFW mode. The
existing public/social/ad workflows stay SFW. Adult workflows are explicit routes
for Fanvue, Telegram paid packs, and CRM-managed custom requests.

## Content Lanes

```env
AVATAR_CONTENT_MODES=sfw,adult
AVATAR_DEFAULT_CONTENT_MODE=sfw
AVATAR_ADULT_MODE_ENABLED=true
AVATAR_ADULT_ALLOWED_PLATFORMS=fanvue,telegram
AVATAR_ADULT_REQUIRE_HUMAN_REVIEW=true
```

- `sfw` is the default lane for TikTok, Meta, public previews, lifestyle content,
  product ads, and broad social distribution.
- `adult` is the paid/subscriber lane for Fanvue, Telegram, and future adult CRM
  requests.
- Adult workflows must pass policy preflight before provider calls or delivery.
- Adult content is not a global switch that changes existing SFW endpoints.

## Adult Preflight Requirements

`POST /adult/policy-check` must pass before future adult generation/delivery jobs:

1. The `adult` content mode is enabled.
2. The target platform is on the allowlist.
3. The persona/subject carries consent attestation.
4. The CRM/operator confirms subject age verification.
5. AI-generated disclosure is acknowledged for the target platform.
6. The prompt does not request prohibited content.
7. Human review remains required before delivery/publishing.

Prohibited content remains blocked in adult mode, including minors or
age-ambiguous subjects, non-consensual or impaired scenarios, sexual violence,
third-party likeness impersonation, and other platform-prohibited content.

## API Contract

`POST /adult/policy-check`

```json
{
  "platform": "fanvue",
  "prompt": "premium studio set for verified persona",
  "persona_id": "persona_123",
  "subject_age_verified": true,
  "ai_disclosure_acknowledged": true
}
```

If `persona_id` is supplied, the API uses the stored persona consent attestation.
A direct `consent_attestation` boolean is also accepted for CRM-side preflight
before a persona has been created.

```json
{
  "allowed": true,
  "decision": "allowed",
  "platform": "fanvue",
  "reasons": [],
  "requires_human_review": true
}
```

## CRM Boundary

The separate CRM should remain the operations layer: subscribers, payments,
platform connectors, conversation history, campaigns, and analytics. This repo
should remain the generation and policy service.

Recommended CRM calls:

- `POST /adult/policy-check` before accepting a custom request.
- `POST /adult/generate-pack` later, returning a background `job_id`.
- `GET /jobs/{id}` to poll generation progress.
- `POST /content/{id}/review` before delivery can send media.

## Telegram Boundary

Telegram automation should start with approved-content sales and delivery:

1. CRM verifies adult mode, terms acceptance, and buyer state.
2. Bot sends an invoice or paid-media offer.
3. Bot handles `pre_checkout_query` quickly.
4. Bot waits for `successful_payment` before delivery.
5. Delivery sends only approved content.
6. Payment charge IDs and delivery receipts sync back to CRM.
7. Refunds/support are tracked as CRM cases.

New adult media generation should remain human-reviewed until classifier,
platform, and payment-state checks have proven reliable.
