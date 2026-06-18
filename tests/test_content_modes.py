from avatar_studio.config import Settings
from avatar_studio.policy.adult import AdultContentPolicy, AdultPolicyInput


def test_settings_enable_sfw_and_adult_by_default():
    settings = Settings()
    assert settings.enabled_content_modes == ("sfw", "adult")
    assert settings.default_content_mode == "sfw"
    assert settings.adult_content_enabled is True


def test_settings_can_disable_adult_lane():
    settings = Settings(content_modes="sfw")
    assert settings.enabled_content_modes == ("sfw",)
    assert settings.adult_content_enabled is False


def test_adult_policy_uses_settings_content_modes():
    enabled = Settings(content_modes="sfw,adult")
    allowed = AdultContentPolicy.from_settings(enabled).evaluate(
        AdultPolicyInput(
            prompt="premium studio set",
            platform="fanvue",
            consent_attestation=True,
            subject_age_verified=True,
            ai_disclosure_acknowledged=True,
        )
    )
    assert allowed.allowed

    disabled = Settings(content_modes="sfw")
    blocked = AdultContentPolicy.from_settings(disabled).evaluate(
        AdultPolicyInput(
            prompt="premium studio set",
            platform="fanvue",
            consent_attestation=True,
            subject_age_verified=True,
            ai_disclosure_acknowledged=True,
        )
    )
    assert not blocked.allowed
    assert blocked.reasons == ["adult_content_mode_disabled"]
