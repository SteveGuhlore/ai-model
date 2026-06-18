from avatar_studio.policy.adult import AdultContentPolicy, AdultDecision, AdultPolicyInput


def test_adult_policy_disabled_by_default():
    policy = AdultContentPolicy(enabled=False, allowed_platforms=["fanvue"])
    result = policy.evaluate(
        AdultPolicyInput(
            prompt="premium studio set",
            platform="fanvue",
            consent_attestation=True,
            subject_age_verified=True,
            ai_disclosure_acknowledged=True,
        )
    )
    assert result.decision is AdultDecision.DISABLED
    assert not result.allowed
    assert result.reasons == ["adult_mode_disabled"]


def test_adult_policy_allows_verified_allowed_platform():
    policy = AdultContentPolicy(enabled=True, allowed_platforms=["fanvue", "telegram"])
    result = policy.evaluate(
        AdultPolicyInput(
            prompt="premium studio set for verified persona",
            platform="FanVue",
            consent_attestation=True,
            subject_age_verified=True,
            ai_disclosure_acknowledged=True,
        )
    )
    assert result.allowed
    assert result.decision is AdultDecision.ALLOWED
    assert result.platform == "fanvue"
    assert result.requires_human_review is True


def test_adult_policy_blocks_missing_attestations_and_unknown_platform():
    policy = AdultContentPolicy(enabled=True, allowed_platforms=["fanvue"])
    result = policy.evaluate(AdultPolicyInput(prompt="premium studio set", platform="unknown"))
    assert not result.allowed
    assert result.decision is AdultDecision.BLOCKED
    assert "platform_not_allowed" in result.reasons
    assert "missing_consent_attestation" in result.reasons
    assert "missing_subject_age_verification" in result.reasons
    assert "missing_ai_disclosure_acknowledgement" in result.reasons


def test_adult_policy_blocks_prohibited_request_terms():
    policy = AdultContentPolicy(enabled=True, allowed_platforms=["fanvue"])
    result = policy.evaluate(
        AdultPolicyInput(
            prompt="underage themed request",
            platform="fanvue",
            consent_attestation=True,
            subject_age_verified=True,
            ai_disclosure_acknowledged=True,
        )
    )
    assert not result.allowed
    assert "minor_or_age_ambiguous" in result.reasons
