# Adult Mode Policy Spine

This branch introduces the groundwork for a separate adult-content workflow. It
does not turn the existing Creator Studio channels into adult generators. The
current `/generate`, `/generate/product-ad`, `/generate/meta-ad`, `/chat`, and
`/generate-image` paths remain SFW and continue to use the existing gates.

## Operating Model

Adult mode is disabled by default:

```env
AVATAR_ADULT_MODE_ENABLED=false
AVATAR_ADULT_ALLOWED_PLATFORMS=fanvue,telegram
AVATAR_ADULT_REQUIRE_HUMAN_REVIEW=true
```

When enabled, adult workflows must pass a policy preflight before any provider
call or CRM delivery job is allowed:

1. Adult mode must be enabled explicitly.
2. The target platform must be on the configured allowlist.
3. The persona/subject must carry consent attestation.
4. The subject must be age verified by the operator/CRM.
5. AI-generated disclosure must be acknowledged for the target platform.
6. The prompt must not request prohibited content.
7. Generated content must land in review before delivery or publishing.

## API Contract

`POST /adult/policy-check`

Request:

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

Response:

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

The separate CRM should remain the operations layer: subscribers, payment state,
platform connectors, conversation history, and campaign automation. This repo
should remain the generation and policy service.

Recommended next CRM calls:

- `POST /adult/policy-check` before accepting a custom request.
- `POST /adult/generate-pack` later, returning a background `job_id`.
- `GET /jobs/{id}` to poll generation progress.
- `POST /content/{id}/review` before any delivery job can send media.

## Telegram Boundary

Telegram automation should start with approved-content delivery only. The bot can
sell pre-reviewed packs, route custom requests into the CRM, and deliver after a
confirmed payment event. New adult media generation should remain human-reviewed
until the policy, classifier, and platform-specific checks have proven reliable.
