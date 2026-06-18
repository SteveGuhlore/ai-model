"""TikTok publisher scaffold (Content Posting API).

Not wired to live posting. ``publish`` enforces human approval and then, until
the client is audited, returns a ``draft``/``skipped`` result rather than posting
publicly. Implementers must complete the audited Direct-Post flow
(POST /v2/post/publish/video/init/) with a real ``access_token`` from the secret
store before flipping ``dry_run`` off.
"""

from __future__ import annotations

from dataclasses import dataclass

from avatar_studio.publishing.base import Content, PublishResult, require_approved


@dataclass
class TikTokPublisher:
    platform: str = "tiktok"
    access_token: str = ""  # injected from secret store; never logged
    audited: bool = False  # flips true only after passing TikTok's audit
    dry_run: bool = True

    def publish(self, content: Content) -> PublishResult:
        require_approved(content)
        if self.dry_run or not self.audited or not self.access_token:
            return PublishResult(
                platform=self.platform,
                external_id=None,
                status="skipped",
                detail="TikTok posting requires an audited client + token; "
                "complete the Direct-Post flow before enabling.",
            )
        # Live posting intentionally not implemented in the scaffold.
        raise NotImplementedError("complete the audited TikTok Direct-Post integration")
