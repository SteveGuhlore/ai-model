"""Publishing interfaces (Phase 9) — control-plane, human-gated, NO autonomous posting.

This layer is deliberately a scaffold. Two hard external gates make live posting a
human-completed step, not an autonomous one:

  * TikTok: the Content Posting API caps unaudited clients (max 5 users/24h, posts
    forced private/SELF_ONLY) until the client passes TikTok's audit.
  * Meta: programmatic ad creation needs Advanced Access to ``ads_management``
    (App Review + Business Verification).

The one invariant enforced here in code: a publisher will REFUSE to publish any
content that is not ``review_status == APPROVED``. Tokens come from the secret
store/env only and are never logged.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from avatar_studio.store.models import Content, ReviewStatus


class NotApprovedError(RuntimeError):
    """Raised on any attempt to publish content a human has not approved."""


@dataclass
class PublishResult:
    platform: str
    external_id: str | None
    status: str  # "submitted" | "draft" | "skipped"
    detail: str = ""


class Publisher(Protocol):
    platform: str

    def publish(self, content: Content) -> PublishResult: ...


def require_approved(content: Content) -> None:
    """Gate every publish path. Approval is the human-in-the-loop seam."""
    if content.review_status is not ReviewStatus.APPROVED:
        raise NotApprovedError(
            f"content {content.id} is {content.review_status.value}, not approved; "
            "publishing is blocked until a human approves it"
        )
