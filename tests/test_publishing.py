"""Phase 9 — publishing scaffolds. CRITICAL: never publish unapproved content."""

import pytest

from avatar_studio.publishing import (
    MetaPublisher,
    NotApprovedError,
    TikTokPublisher,
    require_approved,
)
from avatar_studio.store.models import Content, ReviewStatus, SafetyStatus


def content(review=ReviewStatus.PENDING):
    return Content(
        persona_id="p",
        channel="tiktok",
        kind="video",
        safety_status=SafetyStatus.PASSED,
        review_status=review,
    )


def test_require_approved_blocks_pending():
    with pytest.raises(NotApprovedError):
        require_approved(content(ReviewStatus.PENDING))


def test_require_approved_blocks_rejected():
    with pytest.raises(NotApprovedError):
        require_approved(content(ReviewStatus.REJECTED))


def test_tiktok_refuses_unapproved():
    with pytest.raises(NotApprovedError):
        TikTokPublisher().publish(content(ReviewStatus.PENDING))


def test_meta_refuses_unapproved():
    with pytest.raises(NotApprovedError):
        MetaPublisher().publish(content(ReviewStatus.PENDING))


def test_tiktok_approved_is_skipped_not_posted_by_default():
    # Approved but unaudited/dry-run -> never actually posts.
    res = TikTokPublisher().publish(content(ReviewStatus.APPROVED))
    assert res.status == "skipped"
    assert res.external_id is None


def test_meta_approved_is_draft_not_submitted_by_default():
    res = MetaPublisher().publish(content(ReviewStatus.APPROVED))
    assert res.status == "draft"
    assert res.external_id is None
