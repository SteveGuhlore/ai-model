"""Adult-mode policy spine.

This module does not generate adult media. It answers a narrower question for
future adult endpoints and the separate CRM: may this request enter an adult
content workflow, and what review/platform constraints apply?

The existing SFW generation routes keep using ``avatar_studio.safety.screen``.
Adult-mode routes must use this policy first, then still run media/text checks
that are appropriate for the target platform before anything is delivered.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable


class AdultDecision(str, Enum):
    DISABLED = "disabled"
    ALLOWED = "allowed"
    BLOCKED = "blocked"


@dataclass(frozen=True)
class AdultPolicyInput:
    prompt: str
    platform: str
    consent_attestation: bool = False
    subject_age_verified: bool = False
    ai_disclosure_acknowledged: bool = False


@dataclass(frozen=True)
class AdultPolicyResult:
    decision: AdultDecision
    platform: str
    allowed: bool = False
    reasons: list[str] = field(default_factory=list)
    requires_human_review: bool = True


_PROHIBITED_PATTERNS: list[tuple[str, str]] = [
    (
        "minor_or_age_ambiguous",
        r"\b(minor|under\s*age|underage|child|teen|schoolgirl|schoolboy|17|16|15)\b",
    ),
    (
        "nonconsensual_or_impaired",
        r"\b(non[-\s]?consensual|without\s+consent|asleep|unconscious|drugged|drunk|"
        r"coerc\w*|forced|blackmail|revenge|leaked)\b",
    ),
    (
        "sexual_violence",
        r"\b(rape|assault|violent|violence|blood|injur\w*)\b",
    ),
    (
        "third_party_likeness",
        r"\b(celebrity|public\s+figure|look\s+like|impersonat\w*|deepfake\s+of)\b",
    ),
    (
        "non_human_sexual_content",
        r"\b(animal|bestiality|zoo(?:philia)?)\b",
    ),
]


class AdultContentPolicy:
    """Policy gate for future adult workflows.

    It is intentionally stricter than a prompt parser: missing consent, missing
    age verification, missing AI disclosure, unknown platform, or prohibited
    request terms all block the workflow before any provider call can happen.
    """

    def __init__(
        self,
        *,
        enabled: bool = False,
        allowed_platforms: Iterable[str] = (),
        require_human_review: bool = True,
    ) -> None:
        self.enabled = enabled
        self.allowed_platforms = {p.strip().lower() for p in allowed_platforms if p.strip()}
        self.require_human_review = require_human_review

    @classmethod
    def from_settings(cls, settings) -> "AdultContentPolicy":
        platforms = str(getattr(settings, "adult_allowed_platforms", "")).split(",")
        return cls(
            enabled=bool(getattr(settings, "adult_content_enabled", False)),
            allowed_platforms=platforms,
            require_human_review=bool(getattr(settings, "adult_require_human_review", True)),
        )

    def evaluate(self, inp: AdultPolicyInput) -> AdultPolicyResult:
        platform = (inp.platform or "").strip().lower()
        reasons: list[str] = []

        if not self.enabled:
            return AdultPolicyResult(
                AdultDecision.DISABLED,
                platform=platform,
                allowed=False,
                reasons=["adult_content_mode_disabled"],
                requires_human_review=self.require_human_review,
            )

        if platform not in self.allowed_platforms:
            reasons.append("platform_not_allowed")
        if not inp.consent_attestation:
            reasons.append("missing_consent_attestation")
        if not inp.subject_age_verified:
            reasons.append("missing_subject_age_verification")
        if not inp.ai_disclosure_acknowledged:
            reasons.append("missing_ai_disclosure_acknowledgement")

        reasons.extend(_classify_prohibited(inp.prompt))
        reasons = sorted(set(reasons))
        if reasons:
            return AdultPolicyResult(
                AdultDecision.BLOCKED,
                platform=platform,
                allowed=False,
                reasons=reasons,
                requires_human_review=self.require_human_review,
            )

        return AdultPolicyResult(
            AdultDecision.ALLOWED,
            platform=platform,
            allowed=True,
            reasons=[],
            requires_human_review=self.require_human_review,
        )


def _classify_prohibited(text: str) -> list[str]:
    value = text or ""
    return [label for label, pattern in _PROHIBITED_PATTERNS if re.search(pattern, value, re.I)]

