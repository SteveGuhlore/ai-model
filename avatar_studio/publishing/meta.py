"""Meta publisher scaffold (Marketing API v25.0).

Not wired to live ad creation. ``publish`` enforces human approval and returns a
``draft`` result. Implementers must complete the Campaign -> AdSet -> AdCreative
-> Ad flow with a System User token (Advanced Access to ads_management, which
needs App Review + Business Verification) before flipping ``dry_run`` off.
"""

from __future__ import annotations

from dataclasses import dataclass

from avatar_studio.publishing.base import Content, PublishResult, require_approved


@dataclass
class MetaPublisher:
    platform: str = "meta"
    access_token: str = ""  # System User token from secret store; never logged
    ad_account_id: str = ""
    advanced_access: bool = False  # true only after App Review + Business Verification
    dry_run: bool = True

    def publish(self, content: Content) -> PublishResult:
        require_approved(content)
        if self.dry_run or not self.advanced_access or not self.access_token:
            return PublishResult(
                platform=self.platform,
                external_id=None,
                status="draft",
                detail="Meta ad creation needs Advanced Access to ads_management "
                "(App Review + Business Verification). Assemble the ad-set draft, "
                "then submit manually until access is granted.",
            )
        raise NotImplementedError("complete the Meta Marketing API ad-creation flow")
