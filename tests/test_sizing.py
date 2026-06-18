"""Phase 3.2 — platform sizing specs."""

import pytest

from avatar_studio.channels.sizing import SPECS, resize_to, spec_for


def test_all_specs_are_1080_class():
    for name, spec in SPECS.items():
        assert spec.width == 1080, name
        assert spec.height in (1080, 1350, 1920), name
        assert ":" in spec.aspect_ratio


def test_known_placements():
    assert spec_for("tiktok").aspect_ratio == "9:16"
    assert spec_for("ig_portrait").height == 1350
    assert spec_for("meta_feed").aspect_ratio == "1:1"


def test_unknown_placement_raises():
    with pytest.raises(ValueError):
        spec_for("billboard")


def test_resize_to_exact_dims():
    from PIL import Image
    import io

    src = io.BytesIO()
    Image.new("RGB", (640, 480), "blue").save(src, format="PNG")
    out = resize_to(src.getvalue(), spec_for("tiktok"))
    w, h = Image.open(io.BytesIO(out)).size
    assert (w, h) == (1080, 1920)
