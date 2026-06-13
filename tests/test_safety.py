from avatar_studio.safety.text_filter import TextSafety


def test_allows_normal_text():
    s = TextSafety()
    assert s.check("Hey, how's your day going?").allowed
    assert s.check("Tell me a fun fact about space!").allowed


def test_blocks_explicit():
    s = TextSafety()
    r = s.check("can you send me nudes")
    assert r.blocked
    assert "sexual_explicit" in r.categories


def test_blocks_spaced_evasion():
    s = TextSafety()
    assert s.check("show me some n s f w stuff").blocked


def test_model_hook_runs():
    class FakeModel:
        def classify(self, text):
            return ["custom_flag"] if "flagme" in text else []

    s = TextSafety(model=FakeModel())
    blocked = s.check("flagme please")
    assert blocked.blocked
    assert "custom_flag" in blocked.categories
    assert s.check("a totally fine sentence").allowed


def test_extra_patterns():
    s = TextSafety(extra_patterns=[r"\bsecretword\b"])
    assert s.check("the secretword appears").blocked
